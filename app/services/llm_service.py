"""Integration with Ollama for qualitative code analysis."""
import json
import logging
from pathlib import Path
from typing import Optional, Tuple

import httpx

import config

logger = logging.getLogger(__name__)

LLM_SYSTEM_PROMPT = """Você é um avaliador de código C/C++ para uma disciplina de
Programação Concorrente universitária. Analise o código do aluno e produza:

1. NOTA (0-10): baseada na rubrica fornecida
2. PONTOS POSITIVOS: o que o aluno fez bem
3. PONTOS A MELHORAR: erros, más práticas, oportunidades
4. BUGS DE CONCORRÊNCIA: race conditions, deadlocks, leaks
5. SUGESTÕES: como o aluno pode melhorar

Responda APENAS com JSON válido, sem markdown:
{
  "score": 7.5,
  "positive": ["..."],
  "improvements": ["..."],
  "concurrency_bugs": ["..."],
  "suggestions": ["..."]
}"""


def is_available() -> bool:
    """Check if Ollama is reachable."""
    if not config.LLM_ENABLED:
        return False
    try:
        r = httpx.get(f"{config.LLM_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def analyze_code(
    code: str,
    rubric: str,
    context: str = "",
) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """Send code to Ollama for analysis.

    Returns (score, feedback_markdown, raw_json) or (None, None, error_msg) on failure.
    """
    if not config.LLM_ENABLED:
        return None, None, "LLM desabilitada"

    # Truncate code if too long
    if len(code) > config.LLM_MAX_CODE_LENGTH:
        code = code[:config.LLM_MAX_CODE_LENGTH] + "\n\n... [código truncado]"

    user_prompt = f"""## Rubrica
{rubric}

## Contexto
{context}

## Código do aluno
```c
{code}
```

Avalie o código acima seguindo a rubrica. Responda em JSON."""

    try:
        response = httpx.post(
            f"{config.LLM_BASE_URL}/api/chat",
            json={
                "model": config.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2048,
                },
            },
            timeout=config.LLM_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("LLM timeout")
        return None, None, "LLM timeout"
    except Exception as e:
        logger.warning(f"LLM request failed: {e}")
        return None, None, f"Erro na LLM: {str(e)}"

    try:
        data = response.json()
        content = data.get("message", {}).get("content", "")
    except Exception:
        return None, None, "Resposta inválida da LLM"

    # Parse JSON from response (may be wrapped in ```json blocks)
    score, feedback = _parse_llm_response(content)
    return score, feedback, content


def _parse_llm_response(content: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract score and build feedback markdown from LLM JSON response."""
    # Strip markdown code fences if present
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                return None, _fallback_feedback(content)
        else:
            return None, _fallback_feedback(content)

    score = data.get("score")
    if score is not None:
        try:
            score = float(score)
            score = max(0.0, min(10.0, score))
        except (ValueError, TypeError):
            score = None

    # Build markdown feedback
    parts = []

    positives = data.get("positive", [])
    if positives:
        parts.append("**Pontos positivos:**")
        for p in positives:
            parts.append(f"- {p}")

    improvements = data.get("improvements", [])
    if improvements:
        parts.append("\n**Pontos a melhorar:**")
        for p in improvements:
            parts.append(f"- {p}")

    bugs = data.get("concurrency_bugs", [])
    if bugs:
        parts.append("\n**Bugs de concorrência:**")
        for p in bugs:
            parts.append(f"- {p}")

    suggestions = data.get("suggestions", [])
    if suggestions:
        parts.append("\n**Sugestões:**")
        for p in suggestions:
            parts.append(f"- {p}")

    feedback = "\n".join(parts) if parts else content

    return score, feedback


def _fallback_feedback(content: str) -> str:
    """When JSON parsing fails, return raw content as feedback."""
    return f"*(Resposta da LLM não pôde ser parseada como JSON)*\n\n{content[:3000]}"


def read_source_files(source_dir: Path) -> str:
    """Read all C/C++ source files from a directory into a single string."""
    extensions = {".c", ".h", ".cpp", ".cc", ".hpp"}
    parts = []
    for f in sorted(source_dir.rglob("*")):
        if f.is_file() and f.suffix in extensions:
            try:
                content = f.read_text(errors="replace")
                parts.append(f"// === {f.name} ===\n{content}")
            except Exception:
                continue
    return "\n\n".join(parts)[:config.LLM_MAX_CODE_LENGTH]

"""Helgrind (Valgrind) integration for detecting data races."""
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import config


@dataclass
class HelgrindConfig:
    args: list = None
    timeout_sec: int = 60
    max_errors: int = 0

    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class HelgrindResult:
    ok: bool  # True if errors <= max_errors
    error_count: int
    output: str  # raw helgrind output (truncated)
    error_message: Optional[str] = None


def run_helgrind(binary_path: Path, cfg: HelgrindConfig, cwd: Path) -> HelgrindResult:
    """Run valgrind --tool=helgrind on the binary."""
    cmd = [
        config.VALGRIND_PATH,
        "--tool=helgrind",
        "--error-exitcode=1",
        str(binary_path),
    ] + cfg.args

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=cfg.timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return HelgrindResult(
            ok=False,
            error_count=-1,
            output="",
            error_message=f"Helgrind timeout ({cfg.timeout_sec}s)",
        )
    except FileNotFoundError:
        return HelgrindResult(
            ok=False,
            error_count=-1,
            output="",
            error_message=f"valgrind não encontrado em {config.VALGRIND_PATH}",
        )

    stderr = proc.stderr or ""

    # Parse error count from "ERROR SUMMARY: N errors"
    match = re.search(r"ERROR SUMMARY:\s+(\d+)\s+error", stderr)
    error_count = int(match.group(1)) if match else 0

    # Also count "Possible data race" occurrences
    race_count = stderr.count("Possible data race")

    total_errors = max(error_count, race_count)
    ok = total_errors <= cfg.max_errors

    # Truncate output for storage
    output = stderr[:5000]

    return HelgrindResult(
        ok=ok,
        error_count=total_errors,
        output=output,
    )


def parse_helgrind_config(grading_config: dict) -> Optional[HelgrindConfig]:
    """Parse helgrind config from grading_config JSON."""
    hg = grading_config.get("helgrind")
    if not hg or not hg.get("enabled", False):
        return None
    return HelgrindConfig(
        args=hg.get("args", []),
        timeout_sec=hg.get("timeout_sec", 60),
        max_errors=hg.get("max_errors", 0),
    )

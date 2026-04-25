#!/usr/bin/env python3
"""
Seed de demonstração: cria professor, alunos e dois trabalhos com configuração
completa para testar todo o fluxo do sistema.

Uso:
    python scripts/seed_demo.py

Depois:
    - Acesse http://localhost:8000
    - Login professor: bidu@lavid.ufpb.br / prof123
    - Login aluno:     ana@aluno.ufpb.br  / aluno123
    - Login aluno:     carlos@aluno.ufpb.br / aluno123

Soluções de teste ficam em storage/demo_solutions/ como ZIPs prontos para upload.
"""
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import Assignment, User
from app.security import hash_password

import config

Base.metadata.create_all(bind=engine)

# ─── Soluções de referência (código C) ────────────────────────────────────────

SOMA_CORRETO = r"""
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Uso: %s <a> <b>\n", argv[0]);
        return 1;
    }
    int a = atoi(argv[1]);
    int b = atoi(argv[2]);
    printf("%d\n", a + b);
    return 0;
}
"""

SOMA_ERRADO = r"""
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc < 3) { fprintf(stderr, "Uso: %s <a> <b>\n", argv[0]); return 1; }
    int a = atoi(argv[1]);
    int b = atoi(argv[2]);
    // Bug: subtrai em vez de somar
    printf("%d\n", a - b);
    return 0;
}
"""

SOMA_NAO_COMPILA = r"""
#include <stdio.h>
// Falta fechar a função
int main() {
    printf("hello\n")
"""

COUNTER_CORRETO = r"""
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

static int counter = 0;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

void *increment(void *arg) {
    int n = *(int *)arg;
    for (int i = 0; i < n; i++) {
        pthread_mutex_lock(&lock);
        counter++;
        pthread_mutex_unlock(&lock);
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    int threads = 2, iters = 1000000;
    if (argc >= 2) threads = atoi(argv[1]);
    if (argc >= 3) iters = atoi(argv[2]);

    pthread_t tids[threads];
    for (int i = 0; i < threads; i++)
        pthread_create(&tids[i], NULL, increment, &iters);
    for (int i = 0; i < threads; i++)
        pthread_join(tids[i], NULL);

    pthread_mutex_destroy(&lock);
    printf("%d\n", counter);
    return 0;
}
"""

COUNTER_COM_RACE = r"""
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

static int counter = 0;
// BUG: sem mutex!

void *increment(void *arg) {
    int n = *(int *)arg;
    for (int i = 0; i < n; i++) {
        counter++;  // race condition
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    int threads = 2, iters = 1000000;
    if (argc >= 2) threads = atoi(argv[1]);
    if (argc >= 3) iters = atoi(argv[2]);

    pthread_t tids[threads];
    for (int i = 0; i < threads; i++)
        pthread_create(&tids[i], NULL, increment, &iters);
    for (int i = 0; i < threads; i++)
        pthread_join(tids[i], NULL);

    printf("%d\n", counter);
    return 0;
}
"""


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content.strip() + "\n")
    return buf.getvalue()


def main():
    db = SessionLocal()

    print("=== LPII AutoGrader — Seed de Demonstração ===\n")

    # ─── Professor ────────────────────────────────────────────────────────────
    prof = db.query(User).filter(User.email == "bidu@lavid.ufpb.br").first()
    if not prof:
        prof = User(
            name="Prof. Bidu",
            email="bidu@lavid.ufpb.br",
            password_hash=hash_password("prof123"),
            role="professor",
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)
        print(f"  Professor criado: bidu@lavid.ufpb.br / prof123 (id={prof.id})")
    else:
        print(f"  Professor já existe (id={prof.id})")

    # ─── Alunos ───────────────────────────────────────────────────────────────
    alunos_data = [
        ("Ana Oliveira", "ana@aluno.ufpb.br", "20210001"),
        ("Carlos Mendes", "carlos@aluno.ufpb.br", "20210002"),
        ("Juliana Costa", "juliana@aluno.ufpb.br", "20210003"),
    ]
    for name, email, mat in alunos_data:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(
                name=name, email=email, matricula=mat,
                password_hash=hash_password("aluno123"),
                role="student",
            ))
            print(f"  Aluno criado: {email} / aluno123 ({mat})")
        else:
            print(f"  Aluno já existe: {email}")
    db.commit()

    # ─── Trabalho 1: Soma Simples (sem threads, sem stress) ──────────────────
    deadline1 = datetime.now() + timedelta(days=14)

    grading1 = {
        "compile": {"entry_point": "soma.c", "binary_name": "soma"},
        "compile_weight": 2.0,
        "tests_weight": 8.0,
        "stress_weight": 0,
        "helgrind_weight": 0,
        "llm_weight": 0,
        "tests": [
            {
                "name": "2 + 3 = 5",
                "args": ["2", "3"],
                "timeout_sec": 5,
                "expected_output_contains": "5",
                "points": 2.0,
            },
            {
                "name": "10 + 20 = 30",
                "args": ["10", "20"],
                "timeout_sec": 5,
                "expected_output_contains": "30",
                "points": 2.0,
            },
            {
                "name": "0 + 0 = 0",
                "args": ["0", "0"],
                "timeout_sec": 5,
                "expected_output_contains": "0",
                "points": 2.0,
            },
            {
                "name": "-5 + 3 = -2",
                "args": ["-5", "3"],
                "timeout_sec": 5,
                "expected_output_contains": "-2",
                "points": 2.0,
            },
        ],
    }

    description1 = """# Trabalho 1 — Soma de Dois Inteiros

## Objetivo

Escreva um programa em C que receba dois números inteiros como argumentos de linha de comando e imprima a soma.

## Uso

```
./soma <a> <b>
```

## Exemplos

```bash
./soma 2 3    # Saída: 5
./soma 10 20  # Saída: 30
./soma -5 3   # Saída: -2
```

## Requisitos

1. Receber dois argumentos via `argv`
2. Converter com `atoi()`
3. Imprimir apenas o resultado (um número por linha)
4. Retornar 0 em caso de sucesso, 1 se argumentos insuficientes

## Entrega

- Arquivo: `soma.c`
- Upload via ZIP
"""

    a1 = db.query(Assignment).filter(Assignment.title == "Soma de Dois Inteiros").first()
    if not a1:
        a1 = Assignment(
            title="Soma de Dois Inteiros",
            description=description1,
            module=1,
            max_score=10.0,
            deadline=deadline1,
            status="published",
            compile_flags="-Wall -Wextra",
            expected_files=json.dumps(["soma.c"]),
            grading_config=json.dumps(grading1),
            created_by=prof.id,
        )
        db.add(a1)
        db.commit()
        print(f"\n  Trabalho 1 criado: \"{a1.title}\" (id={a1.id})")
        print(f"    Prazo: {deadline1.strftime('%d/%m/%Y %H:%M')}")
        print(f"    4 testes, sem stress/helgrind/LLM")
    else:
        print(f"\n  Trabalho 1 já existe (id={a1.id})")

    # ─── Trabalho 2: Contador com Threads (stress + helgrind) ────────────────
    deadline2 = datetime.now() + timedelta(days=21)

    grading2 = {
        "compile": {"entry_point": "counter.c", "binary_name": "counter"},
        "compile_weight": 1.0,
        "tests_weight": 4.0,
        "stress_weight": 3.0,
        "helgrind_weight": 2.0,
        "llm_weight": 0,
        "tests": [
            {
                "name": "2 threads × 1M = 2000000",
                "args": ["2", "1000000"],
                "timeout_sec": 15,
                "expected_output_contains": "2000000",
                "points": 2.0,
            },
            {
                "name": "4 threads × 500K = 2000000",
                "args": ["4", "500000"],
                "timeout_sec": 15,
                "expected_output_contains": "2000000",
                "points": 2.0,
            },
        ],
        "stress": {
            "enabled": True,
            "runs": 10,
            "args": ["2", "100000"],
            "expected_output_contains": "200000",
            "timeout_sec": 10,
        },
        "helgrind": {
            "enabled": True,
            "args": ["2", "1000"],
            "timeout_sec": 60,
            "max_errors": 0,
        },
    }

    description2 = """# Trabalho 2 — Contador Concorrente

## Objetivo

Implemente um programa que cria N threads, cada uma incrementando um contador compartilhado M vezes. O resultado final deve ser exatamente `N × M`.

## Uso

```
./counter <num_threads> <incrementos_por_thread>
```

## Exemplos

```bash
./counter 2 1000000   # Saída: 2000000
./counter 4 500000    # Saída: 2000000
```

## Requisitos

1. Usar `pthread_create` / `pthread_join`
2. Proteger o contador com `pthread_mutex_t`
3. Resultado deve ser **sempre** correto (sem race conditions)
4. Imprimir apenas o valor final do contador

## Avaliação

| Critério | Peso |
|---|---|
| Compilação | 1.0 |
| Testes funcionais (resultado correto) | 4.0 |
| Stress test (10 execuções consistentes) | 3.0 |
| Helgrind: 0 data races | 2.0 |

## Dica

Sem mutex, o resultado será inconsistente devido a race conditions. Use `pthread_mutex_lock` / `pthread_mutex_unlock` para proteger a seção crítica.

## Entrega

- Arquivo: `counter.c`
- Upload via ZIP
"""

    a2 = db.query(Assignment).filter(Assignment.title == "Contador Concorrente").first()
    if not a2:
        a2 = Assignment(
            title="Contador Concorrente",
            description=description2,
            module=2,
            max_score=10.0,
            deadline=deadline2,
            status="published",
            compile_flags="-Wall -Wextra -pthread -g",
            expected_files=json.dumps(["counter.c"]),
            grading_config=json.dumps(grading2),
            created_by=prof.id,
        )
        db.add(a2)
        db.commit()
        print(f"\n  Trabalho 2 criado: \"{a2.title}\" (id={a2.id})")
        print(f"    Prazo: {deadline2.strftime('%d/%m/%Y %H:%M')}")
        print(f"    2 testes + stress (10 runs) + helgrind")
    else:
        print(f"\n  Trabalho 2 já existe (id={a2.id})")

    # ─── Gerar ZIPs de solução para teste ────────────────────────────────────
    demo_dir = config.STORAGE_DIR / "demo_solutions"
    demo_dir.mkdir(parents=True, exist_ok=True)

    solutions = {
        "trab1_correto.zip":       {"soma.c": SOMA_CORRETO},
        "trab1_errado.zip":        {"soma.c": SOMA_ERRADO},
        "trab1_nao_compila.zip":   {"soma.c": SOMA_NAO_COMPILA},
        "trab2_correto.zip":       {"counter.c": COUNTER_CORRETO},
        "trab2_com_race.zip":      {"counter.c": COUNTER_COM_RACE},
    }

    print(f"\n  Soluções de teste em {demo_dir}/")
    for filename, files in solutions.items():
        path = demo_dir / filename
        path.write_bytes(make_zip(files))
        print(f"    {filename}")

    db.close()

    print(f"""
{'='*60}
Pronto! Para testar:

  1. Inicie o servidor:
     python main.py

  2. Inicie o worker (outro terminal):
     python grader/worker.py

  3. Acesse http://localhost:8000

  Contas:
    Professor: bidu@lavid.ufpb.br / prof123
    Aluna:     ana@aluno.ufpb.br  / aluno123
    Aluno:     carlos@aluno.ufpb.br / aluno123
    Aluna:     juliana@aluno.ufpb.br / aluno123

  Soluções para upload (em {demo_dir}/):
    Trabalho 1 (Soma):
      trab1_correto.zip       → nota 10.0
      trab1_errado.zip        → nota parcial (compilação OK, testes falham)
      trab1_nao_compila.zip   → nota 0.0

    Trabalho 2 (Contador):
      trab2_correto.zip       → nota alta (testes + stress + helgrind OK)
      trab2_com_race.zip      → stress falha, helgrind detecta races
{'='*60}
""")


if __name__ == "__main__":
    main()

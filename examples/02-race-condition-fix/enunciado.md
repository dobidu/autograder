# Trabalho 2 — Corrigir Race Condition

## Contexto

O programa abaixo cria 2 threads, cada uma incrementando um contador global 1.000.000 de vezes. O resultado esperado é **2.000.000**, mas devido a uma **race condition**, o valor final é frequentemente menor.

```c
#include <stdio.h>
#include <pthread.h>

int counter = 0;

void *increment(void *arg) {
    for (int i = 0; i < 1000000; i++) {
        counter++;  // BUG: race condition!
    }
    return NULL;
}

int main() {
    pthread_t t1, t2;
    pthread_create(&t1, NULL, increment, NULL);
    pthread_create(&t2, NULL, increment, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    printf("%d\n", counter);
    return 0;
}
```

## Tarefa

Corrija o programa acima usando **`pthread_mutex_t`** para eliminar a race condition. O resultado deve ser **sempre** 2.000.000.

## Requisitos

1. Usar `pthread_mutex_lock` / `pthread_mutex_unlock` para proteger o acesso ao contador
2. Inicializar e destruir o mutex corretamente
3. O programa deve imprimir apenas o valor final do contador

## Critérios de Avaliação

| Critério | Peso |
|---|---|
| Compilação sem erros | 1.0 |
| Resultado = 2000000 | 4.0 |
| Stress test (50 execuções consistentes) | 2.5 |
| Helgrind: 0 erros | 1.5 |
| Qualidade de código (LLM) | 1.0 |

## Entrega

- Arquivo: `counter.c`
- Prazo: **05/06/2026 13:59**

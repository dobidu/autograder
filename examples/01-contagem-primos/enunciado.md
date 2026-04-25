# Trabalho 1 — Contagem de Primos Paralela

## Objetivo

Implementar um programa em C que conte a quantidade de números primos no intervalo [2, N], suportando execução **sequencial** e **paralela** (usando `fork()` com comunicação via **pipes** ou **memória compartilhada**).

## Uso

```
./primecount seq <N>
./primecount par <N> <num_processos> <pipe|shm>
```

### Exemplos

```bash
./primecount seq 1000          # Saída: 168
./primecount par 5000000 4 pipe  # Saída: 348513
./primecount par 5000000 8 shm   # Saída: 348513
```

## Requisitos

1. **Modo sequencial (`seq`)**: contar primos de 2 a N em um único processo
2. **Modo paralelo (`par`)**: dividir o intervalo [2, N] entre `num_processos` filhos usando `fork()`
3. **Comunicação**:
   - `pipe`: cada filho envia sua contagem parcial ao pai via pipe
   - `shm`: cada filho escreve sua contagem em memória compartilhada (`shmget`/`mmap`)
4. O pai deve aguardar todos os filhos (`wait`/`waitpid`) e somar os resultados
5. **Saída**: imprimir apenas o número total de primos encontrados

## Critérios de Avaliação

| Critério | Peso |
|---|---|
| Compilação sem erros | 1.0 |
| Testes funcionais (seq + par) | 6.0 |
| Stress test (consistência) | 1.5 |
| Qualidade de código (LLM) | 1.5 |

## Entrega

- Arquivo: `primecount.c`
- Prazo: **15/05/2026 13:59**
- Upload via ZIP ou link de repositório GitHub

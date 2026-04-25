# Trabalho 3 — Produtor-Consumidor

## Objetivo

Implementar o padrão **produtor-consumidor** com buffer circular, usando **mutex** e **variáveis de condição** POSIX (pthreads).

## Uso

```
./prodcon <num_produtores> <num_consumidores> <num_itens>
```

- Cada produtor insere `num_itens` no buffer
- Cada consumidor retira itens até que todos tenham sido consumidos
- Ao final, o programa imprime `OK` se todos os itens produzidos foram consumidos corretamente

### Exemplo

```bash
./prodcon 1 1 10     # 1 produtor, 1 consumidor, 10 itens → OK
./prodcon 2 2 100    # 2 produtores, 2 consumidores, 100 itens cada → OK
```

## Requisitos

1. **Buffer circular** de tamanho fixo (ex: 16 slots)
2. **Mutex** para proteger o acesso ao buffer
3. **Condvar** para sinalizar "buffer não cheio" e "buffer não vazio"
4. Produtores produzem valores sequenciais (1, 2, 3, ...)
5. Consumidores consomem até que todos os itens tenham sido processados
6. Ao final, verificar que a soma dos itens consumidos bate com a esperada
7. Imprimir `OK` se correto, `ERRO` caso contrário

## Critérios de Avaliação

| Critério | Peso |
|---|---|
| Compilação sem erros | 1.0 |
| Testes funcionais | 4.0 |
| Stress test (30 execuções) | 2.0 |
| Helgrind: 0 erros | 2.0 |
| Qualidade de código (LLM) | 1.0 |

## Entrega

- Arquivo: `prodcon.c`
- Prazo: **19/06/2026 13:59**

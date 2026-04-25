/*
 * prodcon.c — Produtor-Consumidor com buffer circular
 * Gabarito do professor
 */
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#define BUF_SIZE 16

typedef struct {
    int buffer[BUF_SIZE];
    int in, out, count;
    int total_produced;
    int total_to_produce;  /* per producer */
    int num_producers;
    int done_producers;
    long sum_produced;
    long sum_consumed;
    pthread_mutex_t mutex;
    pthread_cond_t not_full;
    pthread_cond_t not_empty;
} shared_t;

typedef struct {
    shared_t *shared;
    int items_to_produce;
} producer_arg_t;

typedef struct {
    shared_t *shared;
} consumer_arg_t;

void *producer(void *arg) {
    producer_arg_t *a = (producer_arg_t *)arg;
    shared_t *s = a->shared;

    for (int i = 0; i < a->items_to_produce; i++) {
        pthread_mutex_lock(&s->mutex);
        while (s->count == BUF_SIZE)
            pthread_cond_wait(&s->not_full, &s->mutex);

        int val = ++s->total_produced;
        s->buffer[s->in] = val;
        s->in = (s->in + 1) % BUF_SIZE;
        s->count++;
        s->sum_produced += val;

        pthread_cond_signal(&s->not_empty);
        pthread_mutex_unlock(&s->mutex);
    }

    pthread_mutex_lock(&s->mutex);
    s->done_producers++;
    pthread_cond_broadcast(&s->not_empty);  /* wake consumers to check done */
    pthread_mutex_unlock(&s->mutex);

    return NULL;
}

void *consumer(void *arg) {
    consumer_arg_t *a = (consumer_arg_t *)arg;
    shared_t *s = a->shared;

    while (1) {
        pthread_mutex_lock(&s->mutex);
        while (s->count == 0) {
            if (s->done_producers == s->num_producers) {
                pthread_mutex_unlock(&s->mutex);
                return NULL;
            }
            pthread_cond_wait(&s->not_empty, &s->mutex);
        }

        int val = s->buffer[s->out];
        s->out = (s->out + 1) % BUF_SIZE;
        s->count--;
        s->sum_consumed += val;

        pthread_cond_signal(&s->not_full);
        pthread_mutex_unlock(&s->mutex);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Uso: %s <produtores> <consumidores> <itens_por_produtor>\n", argv[0]);
        return 1;
    }

    int np = atoi(argv[1]);
    int nc = atoi(argv[2]);
    int items = atoi(argv[3]);

    shared_t shared = {
        .in = 0, .out = 0, .count = 0,
        .total_produced = 0,
        .total_to_produce = items,
        .num_producers = np,
        .done_producers = 0,
        .sum_produced = 0,
        .sum_consumed = 0,
        .mutex = PTHREAD_MUTEX_INITIALIZER,
        .not_full = PTHREAD_COND_INITIALIZER,
        .not_empty = PTHREAD_COND_INITIALIZER,
    };

    pthread_t producers[np], consumers[nc];
    producer_arg_t pargs[np];
    consumer_arg_t cargs[nc];

    for (int i = 0; i < np; i++) {
        pargs[i] = (producer_arg_t){.shared = &shared, .items_to_produce = items};
        pthread_create(&producers[i], NULL, producer, &pargs[i]);
    }
    for (int i = 0; i < nc; i++) {
        cargs[i] = (consumer_arg_t){.shared = &shared};
        pthread_create(&consumers[i], NULL, consumer, &cargs[i]);
    }

    for (int i = 0; i < np; i++) pthread_join(producers[i], NULL);
    for (int i = 0; i < nc; i++) pthread_join(consumers[i], NULL);

    pthread_mutex_destroy(&shared.mutex);
    pthread_cond_destroy(&shared.not_full);
    pthread_cond_destroy(&shared.not_empty);

    if (shared.sum_produced == shared.sum_consumed && shared.count == 0)
        printf("OK\n");
    else
        printf("ERRO: produced=%ld consumed=%ld remaining=%d\n",
               shared.sum_produced, shared.sum_consumed, shared.count);

    return 0;
}

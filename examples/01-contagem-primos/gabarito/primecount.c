/*
 * primecount.c — Contagem de primos sequencial e paralela
 * Gabarito do professor
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <math.h>

static int is_prime(long n) {
    if (n < 2) return 0;
    if (n < 4) return 1;
    if (n % 2 == 0 || n % 3 == 0) return 0;
    for (long i = 5; i * i <= n; i += 6) {
        if (n % i == 0 || n % (i + 2) == 0) return 0;
    }
    return 1;
}

static long count_primes_range(long lo, long hi) {
    long count = 0;
    for (long i = lo; i <= hi; i++) {
        if (is_prime(i)) count++;
    }
    return count;
}

static long sequential(long n) {
    return count_primes_range(2, n);
}

static long parallel_pipe(long n, int nprocs) {
    int pipes[nprocs][2];
    for (int i = 0; i < nprocs; i++) {
        if (pipe(pipes[i]) < 0) { perror("pipe"); exit(1); }
    }
    long chunk = (n - 1) / nprocs;
    for (int i = 0; i < nprocs; i++) {
        pid_t pid = fork();
        if (pid < 0) { perror("fork"); exit(1); }
        if (pid == 0) {
            /* Child */
            for (int j = 0; j < nprocs; j++) {
                close(pipes[j][0]);
                if (j != i) close(pipes[j][1]);
            }
            long lo = 2 + i * chunk;
            long hi = (i == nprocs - 1) ? n : lo + chunk - 1;
            long count = count_primes_range(lo, hi);
            write(pipes[i][1], &count, sizeof(count));
            close(pipes[i][1]);
            _exit(0);
        }
    }
    /* Parent */
    long total = 0;
    for (int i = 0; i < nprocs; i++) {
        close(pipes[i][1]);
        long count;
        read(pipes[i][0], &count, sizeof(count));
        close(pipes[i][0]);
        total += count;
    }
    for (int i = 0; i < nprocs; i++) wait(NULL);
    return total;
}

static long parallel_shm(long n, int nprocs) {
    long *shared = mmap(NULL, nprocs * sizeof(long),
        PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (shared == MAP_FAILED) { perror("mmap"); exit(1); }
    memset(shared, 0, nprocs * sizeof(long));

    long chunk = (n - 1) / nprocs;
    for (int i = 0; i < nprocs; i++) {
        pid_t pid = fork();
        if (pid < 0) { perror("fork"); exit(1); }
        if (pid == 0) {
            long lo = 2 + i * chunk;
            long hi = (i == nprocs - 1) ? n : lo + chunk - 1;
            shared[i] = count_primes_range(lo, hi);
            _exit(0);
        }
    }
    for (int i = 0; i < nprocs; i++) wait(NULL);
    long total = 0;
    for (int i = 0; i < nprocs; i++) total += shared[i];
    munmap(shared, nprocs * sizeof(long));
    return total;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Uso: %s <seq|par> <N> [nprocs] [pipe|shm]\n", argv[0]);
        return 1;
    }
    long n = atol(argv[2]);
    long result;

    if (strcmp(argv[1], "seq") == 0) {
        result = sequential(n);
    } else if (strcmp(argv[1], "par") == 0) {
        if (argc < 5) {
            fprintf(stderr, "Uso: %s par <N> <nprocs> <pipe|shm>\n", argv[0]);
            return 1;
        }
        int nprocs = atoi(argv[3]);
        if (strcmp(argv[4], "pipe") == 0) {
            result = parallel_pipe(n, nprocs);
        } else {
            result = parallel_shm(n, nprocs);
        }
    } else {
        fprintf(stderr, "Modo desconhecido: %s\n", argv[1]);
        return 1;
    }
    printf("%ld\n", result);
    return 0;
}

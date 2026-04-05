#include "zsp_fifo.h"
#include <stdlib.h>
#include <assert.h>

void zsp_fifo_init(zsp_fifo_t *f, uint32_t capacity) {
    f->buf   = (uintptr_t *)malloc(capacity * sizeof(uintptr_t));
    f->head  = 0;
    f->tail  = 0;
    f->count = 0;
    f->cap   = capacity;
}

void zsp_fifo_free(zsp_fifo_t *f) {
    free(f->buf);
    f->buf = NULL;
}

bool zsp_fifo_nb_push(zsp_fifo_t *f, uintptr_t val) {
    if (f->count == f->cap) {
        return false;
    }
    f->buf[f->tail] = val;
    f->tail = (f->tail + 1) % f->cap;
    f->count++;
    return true;
}

void zsp_fifo_push(zsp_fifo_t *f, uintptr_t val) {
    assert(f->count < f->cap && "zsp_fifo_push: FIFO full");
    f->buf[f->tail] = val;
    f->tail = (f->tail + 1) % f->cap;
    f->count++;
}

bool zsp_fifo_nb_pop(zsp_fifo_t *f, uintptr_t *out) {
    if (f->count == 0) {
        return false;
    }
    *out    = f->buf[f->head];
    f->head = (f->head + 1) % f->cap;
    f->count--;
    return true;
}

uintptr_t zsp_fifo_pop(zsp_fifo_t *f) {
    assert(f->count > 0 && "zsp_fifo_pop: FIFO empty");
    uintptr_t val = f->buf[f->head];
    f->head = (f->head + 1) % f->cap;
    f->count--;
    return val;
}

uint32_t zsp_fifo_len(zsp_fifo_t *f) {
    return f->count;
}

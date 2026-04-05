#ifndef INCLUDED_ZSP_FIFO_H
#define INCLUDED_ZSP_FIFO_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_fifo_s {
    uintptr_t *buf;
    uint32_t   head, tail, count, cap;
} zsp_fifo_t;

void      zsp_fifo_init(zsp_fifo_t *f, uint32_t capacity);
void      zsp_fifo_free(zsp_fifo_t *f);
bool      zsp_fifo_nb_push(zsp_fifo_t *f, uintptr_t val);
void      zsp_fifo_push(zsp_fifo_t *f, uintptr_t val);
bool      zsp_fifo_nb_pop(zsp_fifo_t *f, uintptr_t *out);
uintptr_t zsp_fifo_pop(zsp_fifo_t *f);
uint32_t  zsp_fifo_len(zsp_fifo_t *f);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_FIFO_H */

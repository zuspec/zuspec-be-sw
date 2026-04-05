#ifndef INCLUDED_ZSP_PAR_BLOCK_H
#define INCLUDED_ZSP_PAR_BLOCK_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_par_block_s {
    int total;
    int done;
} zsp_par_block_t;

void zsp_par_block_init(zsp_par_block_t *p, int n);
void zsp_par_block_fork(zsp_par_block_t *p);
void zsp_par_block_done_one(zsp_par_block_t *p);
bool zsp_par_block_join(zsp_par_block_t *p);
bool zsp_par_block_join_first(zsp_par_block_t *p);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_PAR_BLOCK_H */

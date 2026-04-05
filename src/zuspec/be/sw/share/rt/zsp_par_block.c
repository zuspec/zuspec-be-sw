#include "zsp_par_block.h"

void zsp_par_block_init(zsp_par_block_t *p, int n) {
    p->total = n;
    p->done  = 0;
}

void zsp_par_block_fork(zsp_par_block_t *p) {
    (void)p; /* no-op in cooperative single-threaded model */
}

void zsp_par_block_done_one(zsp_par_block_t *p) {
    p->done++;
}

bool zsp_par_block_join(zsp_par_block_t *p) {
    return p->done == p->total;
}

bool zsp_par_block_join_first(zsp_par_block_t *p) {
    return p->done >= 1;
}

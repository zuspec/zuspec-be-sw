#ifndef INCLUDED_ZSP_SELECT_H
#define INCLUDED_ZSP_SELECT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_select_branch_s {
    int weight;
} zsp_select_branch_t;

typedef struct zsp_select_s {
    zsp_select_branch_t *branches;
    int                  n;
    uint32_t             seed;
} zsp_select_t;

void zsp_select_init(zsp_select_t *s, int n);
void zsp_select_set_weight(zsp_select_t *s, int idx, int weight);
int  zsp_select_weighted_random(zsp_select_t *s);
int  zsp_select_seeded(zsp_select_t *s, uint32_t seed);
void zsp_select_free(zsp_select_t *s);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_SELECT_H */

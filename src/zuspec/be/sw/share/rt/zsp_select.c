#include "zsp_select.h"
#include <stdlib.h>
#include <assert.h>

void zsp_select_init(zsp_select_t *s, int n) {
    s->n        = n;
    s->seed     = 1u;
    s->branches = (zsp_select_branch_t *)malloc((size_t)n * sizeof(zsp_select_branch_t));
    for (int i = 0; i < n; i++) {
        s->branches[i].weight = 1;
    }
}

void zsp_select_set_weight(zsp_select_t *s, int idx, int weight) {
    assert(idx >= 0 && idx < s->n && "zsp_select_set_weight: idx out of range");
    s->branches[idx].weight = weight;
}

static int _select_with_seed(zsp_select_t *s, uint32_t seed) {
    int total = 0;
    for (int i = 0; i < s->n; i++) {
        total += s->branches[i].weight;
    }
    assert(total > 0 && "zsp_select: total weight is zero");

    /* xorshift32 */
    seed ^= seed << 13;
    seed ^= seed >> 17;
    seed ^= seed << 5;
    int pick = (int)(seed % (uint32_t)total);

    for (int i = 0; i < s->n; i++) {
        pick -= s->branches[i].weight;
        if (pick < 0) {
            return i;
        }
    }
    return s->n - 1;
}

int zsp_select_weighted_random(zsp_select_t *s) {
    /* Advance internal seed */
    s->seed ^= s->seed << 13;
    s->seed ^= s->seed >> 17;
    s->seed ^= s->seed << 5;
    return _select_with_seed(s, s->seed);
}

int zsp_select_seeded(zsp_select_t *s, uint32_t seed) {
    return _select_with_seed(s, seed);
}

void zsp_select_free(zsp_select_t *s) {
    free(s->branches);
    s->branches = NULL;
}

#ifndef INCLUDED_ZSP_MUTEX_H
#define INCLUDED_ZSP_MUTEX_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_mutex_s {
    int units;  /* available units */
    int total;  /* total units */
} zsp_mutex_t;

void zsp_mutex_init(zsp_mutex_t *m, int total_units);
bool zsp_mutex_try_acquire(zsp_mutex_t *m);
int  zsp_mutex_acquire(zsp_mutex_t *m);
void zsp_mutex_release(zsp_mutex_t *m, int unit);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_MUTEX_H */

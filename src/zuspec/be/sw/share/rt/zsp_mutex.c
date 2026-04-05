#include "zsp_mutex.h"
#include <assert.h>

void zsp_mutex_init(zsp_mutex_t *m, int total_units) {
    m->total = total_units;
    m->units = total_units;
}

bool zsp_mutex_try_acquire(zsp_mutex_t *m) {
    if (m->units > 0) {
        m->units--;
        return true;
    }
    return false;
}

int zsp_mutex_acquire(zsp_mutex_t *m) {
    assert(m->units > 0 && "zsp_mutex_acquire: no units available");
    m->units--;
    return m->total - m->units - 1;
}

void zsp_mutex_release(zsp_mutex_t *m, int unit) {
    (void)unit;
    assert(m->units < m->total && "zsp_mutex_release: over-release");
    m->units++;
}

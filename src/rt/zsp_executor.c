
#include "zsp/be/sw/rt/zsp_alloc.h"
#include "zsp/be/sw/rt/zsp_executor.h"

static zsp_frame_t *zsp_executor_default_read8(zsp_thread_t *thread, int32_t idx, va_list *args) {

}

zsp_executor_type_t *zsp_executor__type() {
    static zsp_executor_type_t type;
    static int initialized = 0;

    if (!initialized) {
        type.base = *zsp_component__type();
        type.read8 = &zsp_executor_default_read8;
        initialized = 1;
    }

    return &type;
}

void zsp_executor_init(
    zsp_alloc_t             *alloc,
    zsp_executor_t          *executor,
    const char              *name,
    zsp_component_t         *parent) {
    zsp_component_init(alloc, (zsp_component_t *)executor, name, parent);
    ((zsp_object_t *)executor)->type = zsp_executor__type();
}
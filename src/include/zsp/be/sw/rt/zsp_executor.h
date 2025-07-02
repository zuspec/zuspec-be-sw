
#ifndef INCLUDED_ZSP_EXECUTOR_H
#define INCLUDED_ZSP_EXECUTOR_H
#include "zsp/be/sw/rt/zsp_component.h"
#include "zsp/be/sw/rt/zsp_thread.h"

struct zsp_alloc_s;
struct zsp_api_s;

typedef struct zsp_executor_type_s {
    zsp_component_type_t    base;
    zsp_task_func           read8;
    zsp_task_func           read16;
    zsp_task_func           read32;
    zsp_task_func           read64;
    zsp_task_func           write8;
    zsp_task_func           write16;
    zsp_task_func           write32;
    zsp_task_func           write64;
} zsp_executor_type_t;

typedef struct zsp_executor_s {
    zsp_component_t         base;
    struct zsp_api_s        *api;

} zsp_executor_t;

zsp_executor_type_t *zsp_executor__type();

void zsp_executor_init(
    struct zsp_alloc_s  *alloc,
    zsp_executor_t      *executor, 
    const char          *name, 
    zsp_component_t     *parent);


#endif /* INCLUDED_ZSP_EXECUTOR_H */


#ifndef INCLUDED_ZSP_EXECUTOR_H
#define INCLUDED_ZSP_EXECUTOR_H
#include "zsp/be/sw/rt/zsp_component.h"
#include "zsp/be/sw/rt/zsp_thread.h"

struct zsp_actor_s;

typedef struct zsp_executor_type_s {
    zsp_component_type_t    super;
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
    zsp_component_t         super;

} zsp_executor_t;


#endif /* INCLUDED_ZSP_EXECUTOR_H */

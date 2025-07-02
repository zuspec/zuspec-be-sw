#ifndef INCLUDED_ZSP_COMPONENT_H
#define INCLUDED_ZSP_COMPONENT_H
#include <stdint.h>
#include "zsp/be/sw/rt/zsp_alloc.h"
#include "zsp/be/sw/rt/zsp_struct.h"
#include "zsp/be/sw/rt/zsp_thread.h"

#ifdef _cplusplus
extern "C" {
#endif

struct zsp_alloc_s;
struct zsp_component_s;
struct zsp_init_ctxt_s;
struct zsp_executor_s;

typedef void (*zsp_component_init_f)(
    struct zsp_init_ctxt_s  *ctxt,
    struct zsp_component_s  *comp,
    const char              *name,
    struct zsp_component_s  *parent);

typedef struct zsp_component_type_s {
    zsp_object_type_t       __base;
    zsp_component_init_f    init;

    zsp_solve_exec_f        do_init;
    zsp_task_func           do_run_start;

} zsp_component_type_t;

typedef struct zsp_component_s {
    zsp_object_t            base;

    struct zsp_component_s  *parent;
    struct zsp_component_s  *sibling;
    struct zsp_component_s  *children;
    const char              *name;
    struct zsp_executor_s   *default_executor;
} zsp_component_t;

/**
 * The root component is augmented a bit to hold
 * a reference to the 
 */
#define zsp_root_component_s(comp_t, executor_t) \
struct { \
  comp_t                    comp; \
  executor_t                exec; \
  struct zsp_actor_base_t   *actor; \
}

void zsp_component_init(
    struct zsp_init_ctxt_s  *ctxt,
    zsp_component_t         *comp,
    const char              *name,
    zsp_component_t         *parent);

zsp_component_type_t *zsp_component__type();

#define zsp_component_type(comp) \
    ((zsp_component_type_t *)zsp_object_type( (comp) ))

#define zsp_component(comp) \
    ((zsp_component_t *)(comp))

#ifdef _cplusplus
}
#endif

#endif /* INCLUDED_ZSP_COMPONENT_H */

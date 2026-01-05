#ifndef INCLUDED_ZSP_COMPONENT_H
#define INCLUDED_ZSP_COMPONENT_H
#include <stdint.h>
#include "zsp_alloc.h"
#include "zsp_map.h"
#include "zsp_struct.h"
#include "zsp_timebase.h"

#ifdef _cplusplus
extern "C" {
#endif

struct zsp_alloc_s;
struct zsp_component_s;
struct zsp_init_ctxt_s;

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

    zsp_solve_exec_f        init_down;
    zsp_solve_exec_f        init_up;

} zsp_component_type_t;

typedef struct zsp_component_s {
    zsp_object_t            base;

    struct zsp_component_s  *parent;
    struct zsp_component_s  *sibling;
    struct zsp_component_s  *children;
    const char              *name;
    // component type -> listof<inst>
    zsp_int_obj_map_t       comp_t_m;
} zsp_component_t;



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

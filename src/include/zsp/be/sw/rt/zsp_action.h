
#ifndef INCLUDED_ZSP_ACTION_H
#define INCLUDED_ZSP_ACTION_H
#include "zsp/be/sw/rt/zsp_struct.h"
#include "zsp/be/sw/rt/zsp_thread.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_alloc_s;
struct zsp_component_type_s;

typedef struct zsp_action_type_s {
    zsp_struct_type_t           base;
    struct zsp_component_type_s *comp_t;
    zsp_task_func               body;

} zsp_action_type_t;

#define zsp_action_type_begin(name) \
name ## _type_t *name ## __type() { \
    static name ## _type_t __type; \
    static int32_t __init = 0; \
    if (!__init) { \
        __init = 1; \
        \
        // Provide sensible defaults \


#define zsp_action_type_end \
    } \
    return &__type; \
}

#define zsp_action_type(obj) ((zsp_action_type_t *)(((zsp_object_t *)(obj))->type))

typedef struct zsp_action_s {
    zsp_struct_t           base;
} zsp_action_t;

zsp_action_type_t *zsp_action__type(void);

void zsp_action_type_init(zsp_action_type_t *t);

void zsp_action_init(
    struct zsp_alloc_s  *alloc,
    zsp_action_t        *this_p);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_ACTION_H */

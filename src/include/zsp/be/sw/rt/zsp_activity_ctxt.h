
#ifndef INCLUDED_ZSP_ACTIVITY_CTXT_H
#define INCLUDED_ZSP_ACTIVITY_CTXT_H
#include "zsp/be/sw/rt/zsp_list.h"
#include "zsp/be/sw/rt/zsp_thread.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_alloc_s;
struct zsp_activity_ctxt_s;
struct zsp_activity_traversal_s;
struct zsp_activity_traverse_s;
struct zsp_component_s;
struct zsp_executor_s;
struct zsp_thread_s;

typedef enum {
    ZSP_ACTIVITY_CTXT_NONE         = 0,
    ZSP_ACTIVITY_CTXT_PRE_TRAVERSE = 1
} zsp_activity_ctxt_flags_e;

typedef struct zsp_activity_ctxt_funcs_s {
    void *(*pre_traverse)(
        struct zsp_activity_ctxt_s      *ctxt,
        struct zsp_thread_s             *thread,
        struct zsp_activity_traversal_s *traversal);
} zsp_activity_ctxt_funcs_t;

typedef struct zsp_activity_ctxt_s {
    zsp_thread_group_t              base;
    struct zsp_activity_ctxt_s      *parent;
    zsp_activity_ctxt_flags_e       flags;
    const zsp_activity_ctxt_funcs_t *funcs;

    struct zsp_alloc_s              *alloc;
    struct zsp_component_s          *comp;

    // Provides storage for threads under this context
    // Note: this is fixed-size storage
    zsp_list_t                      threads;
} zsp_activity_ctxt_t;

void zsp_activity_ctxt_init(
    zsp_activity_ctxt_t     *ctxt,
    zsp_activity_ctxt_t     *parent);

void zsp_activity_ctxt_init_root(
    zsp_activity_ctxt_t     *ctxt,
    struct zsp_alloc_s      *alloc,
    struct zsp_component_s  *comp);    



#ifdef __cplusplus
}   
#endif


#endif /* INCLUDED_ZSP_ACTIVITY_CTXT_H */
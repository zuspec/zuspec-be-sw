
#ifndef INCLUDED_ZSP_ACTIVITY_CTXT_H
#define INCLUDED_ZSP_ACTIVITY_CTXT_H
#include "zsp/be/sw/rt/zsp_thread.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_activity_traverse_s;

typedef enum {
    ZSP_ACTIVITY_CTXT_NONE             = 0,
    ZSP_ACTIVITY_CTXT_PENDING_PARALLEL = 1
} zsp_activity_ctxt_flags_e;

typedef struct zsp_activity_ctxt_s {
    struct zsp_activity_ctxt_s      *parent;
    zsp_activity_ctxt_flags_e       flags;
    zsp_frame_t *(*pre_traverse)(
        struct zsp_activity_ctxt_s      *ctxt, 
        struct zsp_activity_traverse_s  *traverse);
} zsp_activity_ctxt_t;

void zsp_activity_ctxt_init(
    zsp_activity_ctxt_t *ctxt,
    zsp_activity_ctxt_t *parent);


#ifdef __cplusplus
}   
#endif


#endif /* INCLUDED_ZSP_ACTIVITY_CTXT_H */

#include "zsp/be/sw/rt/zsp_activity_ctxt.h"
#include "zsp/be/sw/rt/zsp_activity_traverse.h"

static zsp_frame_t *zsp_activity_ctxt_pre_traverse(
    zsp_thread_t    *thread,
    zsp_frame_t     *frame,
    va_list         *args) {
    /*
    if ((ctxt->flags & ZSP_ACTIVITY_CTXT_PENDING_PARALLEL)) {
        ctxt->flags &= ~ZSP_ACTIVITY_CTXT_PENDING_PARALLEL;
        ctxt->parent->pre_traverse(ctxt->parent, traverse);
    }
     */

    // TOOD: Handle binding, etc for traversal
}

void zsp_activity_ctxt_init(
    zsp_activity_ctxt_t *ctxt,
    zsp_activity_ctxt_t *parent) {
//    ctxt->pre_traverse = &zsp_activity_ctxt_pre_traverse;
    ctxt->parent = parent;
    if (parent) {
        ctxt->flags = parent->flags;
    } else {
        ctxt->flags = ZSP_ACTIVITY_CTXT_NONE;
    }
}

void zsp_activity_ctxt_init_root(
    zsp_activity_ctxt_t     *ctxt,
    struct zsp_alloc_s      *alloc,
    struct zsp_component_s  *comp) {
    ctxt->alloc = alloc;
    ctxt->comp = comp;
}


#include "zsp/be/sw/rt/zsp_activity_ctxt_par.h"
#include "zsp/be/sw/rt/zsp_activity_traverse.h"

static void zsp_activity_ctxt_par_pre_traverse(
    zsp_activity_ctxt_t *ctxt,
    zsp_activity_traverse_t *traverse) {
    // Call the parent's pre_traverse method
//    ctxt->parent->pre_traverse(ctxt->parent, traverse);
}

void zsp_activity_ctxt_par_init(
    zsp_activity_ctxt_par_t *ctxt,
    zsp_activity_ctxt_t *parent) {
    zsp_activity_ctxt_init(&ctxt->base, parent);
//    ctxt->base.pre_traverse = &zsp_activity_ctxt_par_pre_traverse;
}

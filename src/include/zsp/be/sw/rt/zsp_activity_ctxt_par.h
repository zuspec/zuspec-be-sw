
#ifndef INCLUDED_ZSP_ACTIVITY_CTXT_PAR_H
#define INCLUDED_ZSP_ACTIVITY_CTXT_PAR_H
#include "zsp/be/sw/rt/zsp_activity_ctxt.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_activity_ctxt_par_s {
    zsp_activity_ctxt_t base; // Base activity context
    // List of threads created for sub-activitiess
    // List of checked-in actions

} zsp_activity_ctxt_par_t;

void zsp_activity_ctxt_par_init(
    zsp_activity_ctxt_par_t     *ctxt, 
    zsp_activity_ctxt_t         *parent);

void zsp_activity_ctxt_par_start(
    zsp_activity_ctxt_par_t     *ctxt, 
    zsp_activity_ctxt_flags_e   flags);


#ifdef __cplusplus
}   
#endif

#endif /* INCLUDED_ZSP_ACTIVITY_CTXT_PAR_H */

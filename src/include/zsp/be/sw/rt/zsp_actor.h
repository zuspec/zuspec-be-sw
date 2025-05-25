#ifndef INCLUDED_ZSP_ACTOR_H
#define INCLUDED_ZSP_ACTOR_H
#include "zsp/be/sw/rt/zsp_api.h"
#include "zsp/be/sw/rt/zsp_action.h"
#include "zsp/be/sw/rt/zsp_actor_base.h"
#include "zsp/be/sw/rt/zsp_component.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_actor_s {
    zsp_actor_base_t    base;
    zsp_component_t     comp;
} zsp_actor_t;

#define zsp_actor(comp_t) struct { \
    zsp_actor_base_t    base; \
    comp_t ## _t        comp; \
    }

void zsp_actor_init(
    zsp_actor_t             *actor, 
    zsp_api_t               *api,
    zsp_component_type_t    *comp_t,
    zsp_action_type_t       *action_t);

#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_ACTOR_H */

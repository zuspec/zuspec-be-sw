
#include "zsp/be/sw/rt/zsp_actor.h"
#include "zsp/be/sw/rt/zsp_component.h"

static void zsp_do_init(zsp_actor_t *actor, zsp_component_t *comp) {
    zsp_component_type(comp)->init_down((struct zsp_component_s *)comp);
    zsp_component_do_init(&actor->comp);
}

void zsp_actor_init(
    zsp_actor_t             *actor, 
    zsp_api_t               *api,
    zsp_component_type_t    *comp_t,
    zsp_action_type_t       *action_t) {

    comp_t->init(actor, &actor->comp, "pss_top", 0);
    
}
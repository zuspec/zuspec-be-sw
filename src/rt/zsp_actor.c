#include <stdarg.h>
#include "zsp/be/sw/rt/zsp_actor.h"
#include "zsp/be/sw/rt/zsp_component.h"

static void zsp_do_init(zsp_actor_t *actor, zsp_component_t *comp) {
//    zsp_component_type(comp)->init_down((struct zsp_component_s *)comp);
//    zsp_component_do_init(&actor->comp);
}

void zsp_actor_init(
    zsp_actor_t             *actor, 
    zsp_api_t               *api,
    zsp_component_type_t    *comp_t,
    zsp_action_type_t       *action_t) {

    comp_t->init(actor, &actor->comp, "pss_top", 0);
    
}

static void zsp_actor_elab_comp(
    zsp_actor_t         *actor, 
    zsp_component_t     *comp) {
    zsp_component_type_t *comp_t = zsp_component_type(comp);

    // First, evaluate init_down
}

void zsp_actor_elab(zsp_actor_t *actor) {
    zsp_component_type(&actor->comp)->do_init(actor, (zsp_struct_t *)&actor->comp);

}

struct zsp_frame_s *zsp_actor_run(
    zsp_actor_t             *actor, 
    struct zsp_thread_s     *thread,
    struct zsp_frame_s      *frame,
    ...) {
    if (!frame) {
        // Initial
        va_list args;
        va_start(args, frame);

        va_end(args);
    }


    return frame;
}
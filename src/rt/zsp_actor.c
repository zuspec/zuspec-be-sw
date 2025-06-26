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

    if (comp_t) {
        comp_t->init(actor, &actor->comp, "pss_top", 0);
    }
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

static struct zsp_frame_s *zsp_actor_trampoline(
    struct zsp_thread_s *thread,
    struct zsp_frame_s  *frame,
    va_list             *args) {
    int initial = (frame == 0);

}

/**
 * Start a new thread 
 */
struct zsp_thread_s *zsp_actor_start(
    zsp_actor_t     *actor,
    zsp_scheduler_t *sched,
    zsp_task_func   actor_task,
    void            *action_args) {
    struct zsp_thread_s *thread;

    // Start a new thread
    thread = zsp_thread_create(
        sched,
//        &actor->base.thread, 
        actor_task,
        ZSP_THREAD_FLAGS_NONE,
        action_args);

    return thread;
}

// User-facing actor is:
// - comp
// - action
// - ? action parameters 

// Services API as:
// - global functions
// - API context functions
//
// 
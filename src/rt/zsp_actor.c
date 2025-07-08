#include <stdarg.h>
#include "zsp/be/sw/rt/zsp_activity_ctxt.h"
#include "zsp/be/sw/rt/zsp_activity_traverse.h"
#include "zsp/be/sw/rt/zsp_actor.h"
#include "zsp/be/sw/rt/zsp_component.h"
#include "zsp/be/sw/rt/zsp_executor.h"
#include "zsp/be/sw/rt/zsp_init_ctxt.h"

static void zsp_do_init(zsp_actor_t *actor, zsp_component_t *comp) {
//    zsp_component_type(comp)->init_down((struct zsp_component_s *)comp);
//    zsp_component_do_init(&actor->comp);
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
    int32_t             idx,
    va_list             *args) {
    zsp_frame_t *ret = thread->leaf;
    struct __locals_s {
        zsp_api_t               *api;
        zsp_component_type_t    *comp_t;
        zsp_action_type_t       *action_t;
        zsp_activity_ctxt_t     ctxt;
        zsp_executor_t          default_exec;
        zsp_component_t         *comp;
    };

    switch (idx) {
        case 0: {
            struct __locals_s *__locals;
            zsp_api_t *api = va_arg(*args, zsp_api_t *);
            zsp_component_type_t *comp_t = va_arg(*args, zsp_component_type_t *);
            zsp_action_type_t *action_t = va_arg(*args, zsp_action_type_t *);
            void *action_args = va_arg(*args, void *);
            zsp_init_ctxt_t init_ctxt;

            ret = zsp_thread_alloc_frame(thread, 
                sizeof(struct __locals_s)+((zsp_object_type_t *)comp_t)->size,
                &zsp_actor_trampoline);
            __locals = zsp_frame_locals(ret, struct __locals_s);
            __locals->api = api;
            __locals->comp_t = comp_t;
            __locals->action_t = action_t;
            __locals->comp = (zsp_component_t *)(__locals + sizeof(struct __locals_s));

            // Initialize the component
            init_ctxt.alloc = 0;
            init_ctxt.api = api;
            comp_t->init(&init_ctxt, __locals->comp, "pss_top", 0);

            // Setup the default executor

            // Elaborate the component
            zsp_component_type(__locals->comp)->do_init(
                &__locals->default_exec,
                (zsp_struct_t *)__locals->comp);

            __locals->ctxt.comp = __locals->comp;

            ret->idx = 1;
            ret = zsp_activity_traverse_type(
                thread,
                &__locals->ctxt,
                action_t,
                0);
        }

        default: {
            if (ret == thread->leaf) {
                ret = zsp_thread_return(thread, 0);
            }
        }
    }

    return ret;
}

/**
 * Start a new thread 
 */
zsp_thread_t *zsp_actor_create(
    zsp_scheduler_t         *sched,
    zsp_api_t               *api,
    zsp_component_type_t    *comp_t,
    zsp_action_type_t       *action_t) {
    struct zsp_thread_s *thread;

    // Start a new thread
    thread = zsp_thread_create(
        sched,
        &zsp_actor_trampoline,
        ZSP_THREAD_FLAGS_NONE,
        api,
        comp_t,
        action_t);

    return thread;
}

void zsp_actor_init(
    zsp_thread_t            *thread, 
    zsp_scheduler_t         *sched,
    zsp_api_t               *api,
    zsp_component_type_t    *comp_t,
    zsp_action_type_t       *action_t) {

    zsp_thread_init(
        sched, 
        thread, 
        &zsp_actor_trampoline,
        ZSP_THREAD_FLAGS_NONE,
        api,
        comp_t,
        action_t);
}

zsp_actor_type_t *zsp_actor_type(zsp_actor_base_t *actor) {
    return actor->type;
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
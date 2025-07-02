
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_action.h"
#include "zsp/be/sw/rt/zsp_activity_ctxt.h"
#include "zsp/be/sw/rt/zsp_activity_traverse.h"
#include "zsp/be/sw/rt/zsp_component.h"
#include "zsp/be/sw/rt/zsp_thread.h"

struct zsp_frame_s *zsp_activity_traverse(
    struct zsp_thread_s         *thread, 
    struct zsp_activity_ctxt_s  *ctxt,
    struct zsp_action_type_s    *action_t) {
    zsp_frame_t *ret =  0;

    // If there's a pre-traverse function, we need to
    // use the trampoline 
    // Otherwise, we can just call the action directly
    ret = zsp_thread_call(thread, action_t->body, action_t, ctxt);

    return ret;
}

static struct zsp_frame_s *zsp_activity_traverse_type_task(
    struct zsp_thread_s         *thread, 
    int32_t                     idx,
    va_list                     *args) {
    typedef struct __locals_s {
        zsp_activity_ctxt_t     *ctxt;
        zsp_action_type_t       *action_t;
        zsp_action_t            *action;
    } __locals_t;

    zsp_frame_t *ret = thread->leaf;

    switch (idx) {
        case 0: {
            __locals_t *__locals;
            zsp_activity_ctxt_t *ctxt = va_arg(*args, zsp_activity_ctxt_t *);
            zsp_action_type_t *action_t = va_arg(*args, zsp_action_type_t *);
            zsp_activity_traverse_init_f init = va_arg(*args, zsp_activity_traverse_init_f);

            ret = zsp_thread_alloc_frame(
                thread, 
                (sizeof(struct __locals_s) + ((zsp_object_type_t *)action_t)->size),
                &zsp_activity_traverse_type_task);
            __locals = zsp_frame_locals(ret, struct __locals_s);
            __locals->action = (zsp_action_t *)__locals + sizeof(struct __locals_s);
            __locals->ctxt = ctxt;
            __locals->action_t = action_t;

            ((zsp_object_type_t *)action_t)->init(0, zsp_object(__locals->action));

            if (init) {
                // Call the traversal's initialization 'hook' method
                // Pass the caller's frame to allow the 'hook' to access 
                // data available to the caller
                init(thread->leaf->prev, __locals->action);
            }

            // TODO: check in with the context if requested
            ret->idx = 1;
        }
        case 1: {
            __locals_t *__locals = zsp_frame_locals(ret, struct __locals_s);
            struct zsp_executor_s *exec_b = __locals->ctxt->comp->default_executor;

            // TODO: prepare the action context if needed

            // Randomize the action
            zsp_struct_call(pre_solve, exec_b, __locals->action);
            // TODO: randomization
            // TODO: Reassess executor (?)
            zsp_struct_call(post_solve, exec_b, __locals->action);

            // Launch the body
            ret->idx = 2;
            ret = zsp_thread_call(
                thread, 
                zsp_action_type(__locals->action)->body,
                __locals->action);
            if (ret) {
                break;
            }
        }
        default: {
            ret = zsp_thread_return(thread, 0);
        }
    }

    return ret;
}

struct zsp_frame_s *zsp_activity_traverse_type(
    struct zsp_thread_s         *thread,
    struct zsp_activity_ctxt_s  *ctxt,
    struct zsp_action_type_s    *action_t,
    zsp_activity_traverse_init_f init) {

    return zsp_thread_call(
        thread, 
        &zsp_activity_traverse_type_task, 
        ctxt,
        action_t,
        init);
}
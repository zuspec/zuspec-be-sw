
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_action.h"
#include "zsp/be/sw/rt/zsp_activity_traverse.h"
#include "zsp/be/sw/rt/zsp_thread.h"

/**
 * component pss_top {
 *   action doit {
 *     exec body {
 *       yield;
 *       print("Hello\n");
 *     }
 *   }
 *   action Entry {
 *     activity {
 *       do doit;
 *       do doit;
 *     }
 *   }
 * }
 */

static zsp_frame_t *pss_top__doit__body(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    fprintf(stdout, "pss_top.doit.body: idx=%d\n", idx);

    switch (idx) {
        case 0: {
            CASE_0:
            ret = zsp_thread_alloc_frame(thread, 0, &pss_top__doit__body);

            // yield
            ret->idx = 1;
            zsp_thread_yield(thread);
            break;
        }
        case 1: {
            CASE_1:
            fprintf(stdout, "Hello World!\n");
        }
        default: {
            ret = zsp_thread_return(thread, 0);
        }
    }

    return ret;
}

typedef struct pss_top__doit_s {
    zsp_action_t    base;
} pss_top__doit_t;

typedef struct pss_top__doit__type_s {
    zsp_action_type_t base;
} pss_top__doit__type_t;

void pss_top__doit_init(struct zsp_actor_s *actor, struct pss_top__doit_s *t);

pss_top__doit__type_t *pss_top__doit_type() {
    static pss_top__doit__type_t __pss_top__doit_type;
    static int initialized = 0;
    if (!initialized) {
        initialized = 1;
        zsp_action_type_init((zsp_action_type_t *)&__pss_top__doit_type);
        ((zsp_object_type_t *)&__pss_top__doit_type)->super = (zsp_object_type_t *)zsp_action__type();
        ((zsp_object_type_t *)&__pss_top__doit_type)->name = "pss_top::doit";
        ((zsp_object_type_t *)&__pss_top__doit_type)->init = (zsp_init_f)&pss_top__doit_init;
        ((zsp_object_type_t *)&__pss_top__doit_type)->size = sizeof(pss_top__doit_t);
        ((zsp_action_type_t *)&__pss_top__doit_type)->comp_t = 0; // Set to the appropriate component type if needed
        ((zsp_action_type_t *)&__pss_top__doit_type)->body = &pss_top__doit__body;
    }
    return &__pss_top__doit_type;
}

void pss_top__doit_init(struct zsp_actor_s *actor, struct pss_top__doit_s *t) {
    zsp_action_init(actor, (zsp_action_t *)t);
    // Initialize other fields if necessary
    ((zsp_object_t *)t)->type = (zsp_object_type_t *)pss_top__doit_type();
}

static zsp_frame_t *pss_top__Entry__body(zsp_thread_t *thread, int idx, va_list *args) {
    typedef struct __locals1_s {
    } __locals1_t;
    zsp_frame_t *ret = thread->leaf;

    switch (idx) {
        case 0: {
            __locals1_t *locals;
            CASE_0:
            ret = zsp_thread_alloc_frame(thread, sizeof(__locals1_t), &pss_top__Entry__body);
            locals = zsp_frame_locals(ret, __locals1_t);

            // Traverse anonymous action instance 'doit' 
            // yield
            ret->idx = 1; // Say where we want to be next time
            ret = zsp_activity_traverse_type(
                thread, 
                0, // No context
                (zsp_action_type_t *)pss_top__doit_type(),
                0); // No 'init' function
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

void main() {
    int i;
    zsp_alloc_t alloc;
    zsp_scheduler_t scheduler;
    zsp_thread_t *thread;

    zsp_alloc_malloc_init(&alloc);

    zsp_scheduler_init(&scheduler, &alloc);

    thread = zsp_thread_create(
        &scheduler, 
        &pss_top__Entry__body, 
        ZSP_THREAD_FLAGS_NONE,
        0 // self
    );

    for (i=0; i<100 && thread->leaf; i++) {
        fprintf(stdout, "Iteration %d\n", i);
        zsp_scheduler_run(&scheduler);
    }

}



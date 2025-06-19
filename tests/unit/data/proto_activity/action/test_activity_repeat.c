
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

//    fprintf(stdout, "pss_top.doit.body: idx=%d\n", idx);

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
//            fprintf(stdout, "Hello World!\n");
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

typedef struct pss_top__Entry_s {
    zsp_action_t        base;
} pss_top__Entry_t;

typedef struct pss_top__Entry__type_s {
    zsp_action_type_t base;
} pss_top__Entry__type_t;

static zsp_frame_t *pss_top__Entry__body(zsp_thread_t *thread, int idx, va_list *args);

pss_top__Entry__type_t *pss_top__Entry__type() {
    static pss_top__Entry__type_t __pss_top__Entry__type;
    static int initialized = 0;
    if (!initialized) {
        initialized = 1;
        zsp_action_type_init((zsp_action_type_t *)&__pss_top__Entry__type);
        ((zsp_object_type_t *)&__pss_top__Entry__type)->super = (zsp_object_type_t *)zsp_action__type();
        ((zsp_object_type_t *)&__pss_top__Entry__type)->name = "pss_top::Entry";
        ((zsp_action_type_t *)&__pss_top__Entry__type)->body = &pss_top__Entry__body;
    }
    return &__pss_top__Entry__type;
}

void ss_top__Entry_init(struct zsp_actor_s *actor, struct pss_top__Entry_s *t) {
    zsp_action_init(actor, (zsp_action_t *)t);
    // Initialize other fields if necessary
    ((zsp_object_t *)t)->type = (zsp_object_type_t *)pss_top__Entry__type();
}

static zsp_frame_t *pss_top__Entry__body(zsp_thread_t *thread, int idx, va_list *args) {
    typedef struct __locals1_s {
        pss_top__Entry_t *self;
    } __locals1_t;
    typedef struct __locals2_s {
        pss_top__Entry_t *self;
        int64_t  i;
    } __locals2_t;
    // Indicies into timewheel
    // - Indicies and entries are offsets
    // - Drop an index every N timesteps?
    // - Possibly distributing by timestep count is better than time 
    const uint64_t IT_MAX = 1_000_000_000; // 47.56 ; 41 opt ; 20 rt opt
    const size_t __max_sz = 
        (sizeof(__locals1_t) > sizeof(__locals2_t)) ? sizeof(__locals1_t) : sizeof(__locals2_t);

    zsp_frame_t *ret = thread->leaf;

//    fprintf(stdout, "pss_top.Entry.body: idx=%d frame=%p\n", idx, ret);
//    fflush(stdout);

    switch (idx) {
        case 0: {
            pss_top__Entry_t *self = (pss_top__Entry_t *)va_arg(*args, pss_top__Entry_t *);
            __locals1_t *locals;
            CASE_0:
            ret = zsp_thread_alloc_frame(thread, __max_sz, &pss_top__Entry__body);
            locals = zsp_frame_locals(ret, __locals1_t);
            fprintf(stdout, "CASE_0: frame=%p\n", ret);
            fflush(stdout);
            ret->idx = 1;
        }
        case 1: { // Enter loop logical scope so we have access to local vars
            __locals2_t *__locals = zsp_frame_locals(ret, __locals2_t);

            __locals->i = 0; // Initialize loop variable
//            fprintf(stdout, "Initialize i (%p)\n", &__locals->i);
//            fflush(stdout);
            // Must move to a new scope that contains
            // the loop-head check
        }
        case 2: { // Top of the loop
            CASE_2:
            __locals2_t *__locals = zsp_frame_locals(ret, __locals2_t);
//            fprintf(stdout, "Test i=%d (%p) ret=%p\n", __locals->i, &__locals->i, ret);
//            fflush(stdout);
            if (!(__locals->i < IT_MAX)) {
                // Loop condition failed, exit loop
                ret->idx = 4;
                goto CASE_4;
            }

            // Otherwise, proceed with loop body
            // No need to create a distinct scope for loop body

            // Traverse anonymous action instance 'doit' 
            ret->idx = 3; // Say where we want to be next time
            ret = zsp_activity_traverse_type(
                thread, 
                0, // No context
                (zsp_action_type_t *)pss_top__doit_type(),
                0);
            if (ret) {
                break;
            }
        }
        case 3: { // After action execution
            CASE_3:
            __locals2_t *__locals = zsp_frame_locals(ret, __locals2_t);
            __locals->i++; // Increment loop variable

            ret->idx = 2; // Go back to loop head 
            goto CASE_2;
        }
        case 4: { // Exit loop
            CASE_4:
            __locals2_t *__locals = zsp_frame_locals(ret, __locals2_t);
            fprintf(stdout, "Exiting loop after %d iterations\n", __locals->i);
            // Could have more non-blocking code here...
        }
        default: {
            fprintf(stdout, "Exiting pss_top.Entry.body\n");
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

    for (i=0; thread->leaf; i++) {
//        fprintf(stdout, "Iteration %d\n", i);
        zsp_scheduler_run(&scheduler);
    }

}



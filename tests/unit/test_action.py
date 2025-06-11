import pytest
import io
import os

from .single_type_utils import run_single_type_test


def test_smoke(tmpdir):
    pss_top = """
component pss_top {
    int a = 5;

    exec init_down {
        print("--> init_down\\n");
    }

    action Inner {
        exec post_solve {
            print("-- post_solve\\n");
        }
    }

    activity {
        do Inner;
    }

    action Entry {
        int v;
        exec pre_solve {
            v = 10;
            print("-- Entry::pre_solve\\n");
        }
    }
}
"""

    test_c = """
#include <stdio.h>
#include <stdlib.h>
#include "zsp/be/sw/rt/zsp_actor.h"
#include "pss_top.h"
#include "pss_top__Entry.h"

void std_pkg__print(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vfprintf(stdout, fmt, args);
    va_end(args);
}

typedef struct pss_top__Entry_args_s {
} pss_top__Entry_args_t;

typedef struct pss_top__Entry_actor_s {
    zsp_actor(pss_top);
    pss_top__Entry_args_t   args;
} pss_top__Entry_actor_t;

static void pss_top__Entry_init_args(pss_top__Entry_t *self, pss_top__Entry_args_t *args) {
}

static zsp_frame_t *pss_top__Entry_actor_entry(
    zsp_thread_t *thread, 
    zsp_frame_t *frame, 
    va_list *args) {
    zsp_frame_t *ret = 0;
    int initial = (frame == 0);
    zsp_actor_t *actor = (zsp_actor_t *)thread;
    struct __locals_s {
      int a;
      int b;
    } *__locals;

    if (!frame) {
        frame = zsp_thread_alloc_frame(thread, sizeof(struct __locals_s), &pss_top__Entry_actor_entry);
    }
    __locals = (struct __locals_s *)&((zsp_frame_wrap_t *)frame)->locals;
    ret = frame;

    fprintf(stdout, "pss_top__Entry_actor_entry called\\n");

    if (initial) {
        __locals->a = 0;
    }

    switch (frame->idx) {
        case 0: {
            fprintf(stdout, "case 0 (%d)\\n", frame->idx);
            frame->idx++;
            ret = zsp_thread_call(thread, 
                zsp_component_type(&actor->comp)->do_run_start,
                &actor->comp, 
                0); // Executor handle to use (passed down)
            if (ret) {
                break;
            }
        }
        case 1: {
            fprintf(stdout, "case 1 (%d)\\n", frame->idx);
            frame->idx++;
            // Run the root activity
        }
        default: {
            ret = zsp_thread_return(thread, frame, 0);
        }
    }

    // Actor runs an instance of the specified action type

    return ret;
}

void pss_top__Entry_actor_init(pss_top__Entry_actor_t *actor, zsp_api_t *api) {
    zsp_actor_init(
        (zsp_actor_t *)actor, 
        api, 
        (zsp_component_type_t *)pss_top__type(),
        (zsp_action_type_t *)pss_top__Entry__type());
}

zsp_thread_t *pss_top__Entry_actor_start(pss_top__Entry_actor_t *actor, zsp_scheduler_t *scheduler) {
    zsp_thread_t *thread;

    zsp_actor_elab((zsp_actor_t *)actor);

    thread = zsp_thread_init(
        scheduler, 
        (zsp_thread_t *)actor, 
        &pss_top__Entry_actor_entry, 
        0);

    return (zsp_thread_t *)actor;
}

static void *local_malloc(zsp_alloc_t *alloc, size_t size) {
    fprintf(stdout, "local_malloc called with size=%zu\\n", size);
    return malloc(size);
}

static void local_free(zsp_alloc_t *alloc, void *ptr) {
    free(ptr);
}

int main() {
    pss_top__Entry_actor_t actor;
    zsp_scheduler_t scheduler;
    zsp_thread_t *thread;
    int i;

    zsp_alloc_t alloc = {
        .alloc = &local_malloc,
        .free = &local_free
    };

    zsp_scheduler_init(&scheduler, &alloc);

    pss_top__Entry_actor_init(&actor, 0);

    thread = pss_top__Entry_actor_start(&actor, &scheduler);

    fprintf(stdout, "RES: comp.a=%d\\n", actor.comp.a);

    // Spin until the actor has finished executing
    for (i=0; i<1000 && thread->leaf; i++) {
        zsp_scheduler_run(&scheduler);
    }

    if (thread->leaf) {
        fprintf(stdout, "Actor did not finish executing\\n");
    } else {
        fprintf(stdout, "Actor finished executing\\n");
    }
}
"""

    exp = """
RES: comp.a=5
"""

    run_single_type_test(
        os.path.join(tmpdir), 
        pss_src=pss_top, 
        typename="pss_top::Entry", 
        c_src=test_c,
        exp=exp,
        debug=True
    )


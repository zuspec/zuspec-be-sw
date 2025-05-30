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

    action Entry {
        int v;
        exec pre_solve {
            v = 10;
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
    int initial = (frame == 0);
    fprintf(stdout, "pss_top__Entry_actor_entry called\\n");

    if (initial) {
    }

    return frame;
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

    zsp_scheduler_thread_init(
        scheduler, 
        (zsp_thread_t *)actor, 
        &pss_top__Entry_actor_entry, 
        0);

    return (zsp_thread_t *)actor;
}

int main() {
    pss_top__Entry_actor_t actor;
    zsp_scheduler_t scheduler;
    zsp_thread_t *thread;
    zsp_alloc_t alloc = {
        .alloc = malloc,
        .free = free
    };

    zsp_scheduler_init(&scheduler, &alloc);

    pss_top__Entry_actor_init(&actor, 0);

    thread = pss_top__Entry_actor_start(&actor, &scheduler);

    fprintf(stdout, "RES: comp.a=%d\\n", actor.comp.a);
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


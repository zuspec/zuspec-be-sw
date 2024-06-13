
#include "hello_world.h"

void pss_top_init(
    pss_top_Entry_actor_t   *actor,
    pss_top_t               *obj) {
}

void pss_top_Sub_init(
    pss_top_Entry_actor_t   *actor,
    pss_top_Sub_t           *obj) {
    ((zsp_rt_task_t *)obj)->func = (zsp_rt_task_f)&pss_top_Sub_run;
}

void pss_top_Sub_exec_body_init(
    pss_top_Entry_actor_t       *actor,
    pss_top_Sub_exec_body_t     *obj) {
    ((zsp_rt_task_t *)obj)->func = (zsp_rt_task_f)&pss_top_Sub_exec_body_run;

}

zsp_rt_task_t *pss_top_Sub_exec_body_run(
    pss_top_Entry_actor_t       *actor,
    pss_top_Sub_exec_body_t     *obj) {
    zsp_rt_task_t *ret = 0;

    switch (((zsp_rt_task_t *)obj)->idx) {
        case 0: {
            ((zsp_rt_task_t *)obj)->idx++;
//            actor->funcs.print_f("Hello World!");
        }
        case 1: {
            ((zsp_rt_task_t *)obj)->idx++;
            ret = zsp_rt_task_leave(
                (zsp_rt_actor_t *)actor,
                ((zsp_rt_task_t *)obj),
                0
            );
        }
    }

    return ret;
}

zsp_rt_task_t *pss_top_Sub_run(
    pss_top_Entry_actor_t   *actor,
    pss_top_Sub_t           *obj) {
    zsp_rt_task_t *ret = 0;

    switch (((zsp_rt_task_t *)obj)->idx) {
        case 0: {
            pss_top_Sub_exec_body_t *body;
            ((zsp_rt_task_t *)obj)->idx++;

            // TODO: invoke solve process

            // TODO: invoke beginning of body
            body = (pss_top_Sub_exec_body_t *)zsp_rt_task_enter(
                (zsp_rt_actor_t *)actor,
                sizeof(pss_top_Sub_exec_body_t),
                (zsp_rt_init_f)&pss_top_Sub_exec_body_init);

            if ((ret=zsp_rt_task_run(
                (zsp_rt_actor_t *)actor, (zsp_rt_task_t *)body))) {
                break;
            }
        }

        case 1: {
            // We're done! Manage return
            ret = zsp_rt_task_leave(
                (zsp_rt_actor_t *)actor,
                ((zsp_rt_task_t *)obj),
                0
            );
        }
    }
    return ret;
}

void pss_top_Entry_init(
    pss_top_Entry_actor_t   *actor,
    pss_top_Entry_t         *obj) {
    ((zsp_rt_task_t *)obj)->func = (zsp_rt_task_f)&pss_top_Entry_run;
    
    // Normally, we'd initialize plain-data fields, etc
    obj->loop_i = 0;
}

zsp_rt_task_t *pss_top_Entry_run(
    pss_top_Entry_actor_t   *actor,
    pss_top_Entry_t         *obj) {
    zsp_rt_task_t *ret = 0;
    int retry = 0;

    do {
        retry = 0;
        ret = 0;
    switch (((zsp_rt_task_t *)obj)->idx) {
        case 0: {
            ((zsp_rt_task_t *)obj)->idx++;
            // Root action always suspends on first call
            ret = (zsp_rt_task_t *)obj;
        } break;
        case 1: {
            pss_top_Sub_t *Sub_1;
            ((zsp_rt_task_t *)obj)->idx++;

            Sub_1 = (pss_top_Sub_t *)zsp_rt_task_enter(
                (zsp_rt_actor_t *)actor,
                sizeof(pss_top_Sub_t),
                (zsp_rt_init_f)&pss_top_Sub_init);

            if ((ret=zsp_rt_task_run(
                (zsp_rt_actor_t *)actor, 
                (zsp_rt_task_t *)Sub_1))) {
                break;
            }
        }
        case 2: {
            pss_top_Sub_t *Sub_2;
            ((zsp_rt_task_t *)obj)->idx++;

            Sub_2 = (pss_top_Sub_t *)zsp_rt_task_enter(
                (zsp_rt_actor_t *)actor,
                sizeof(pss_top_Sub_t),
                (zsp_rt_init_f)&pss_top_Sub_init);

            // TODO: Apply any post_init initialization
            // expressions here.

            if ((ret=zsp_rt_task_run(
                (zsp_rt_actor_t *)actor, (zsp_rt_task_t *)Sub_2))) {
                break;
            }
        }

        case 3: {
            ((zsp_rt_task_t *)obj)->idx++;
            if (++(obj->loop_i) < 100) {
                ((zsp_rt_task_t *)obj)->idx = 1;
                ret = (zsp_rt_task_t *)obj;
                retry = 1;
                break;
            }
        }

        case 4: {
            // All done. Tear down this stack frame 
            // and return the next task to run
            ret = zsp_rt_task_leave(
                (zsp_rt_actor_t *)actor,
                (zsp_rt_task_t *)obj,
                0);
        }
    }
    } while (retry);

    return ret;
}

void pss_top_Entry_actor_init(pss_top_Entry_actor_t *actor) {
    pss_top_Entry_t *root_action;

    zsp_rt_actor_init((zsp_rt_actor_t *)actor);

    // Initialize the component tree
    pss_top_init(actor, &actor->root_comp);

    // Create the root action and add it as a task
    root_action = (pss_top_Entry_t *)zsp_rt_task_enter(
        (zsp_rt_actor_t *)actor,
        sizeof(pss_top_Entry_t),
        (zsp_rt_init_f)&pss_top_Entry_init);

    zsp_rt_task_run(
        (zsp_rt_actor_t *)actor,
        (zsp_rt_task_t *)root_action
    );

    zsp_rt_queue_task(
        (zsp_rt_actor_t *)actor,
        (zsp_rt_task_t *)root_action);
}



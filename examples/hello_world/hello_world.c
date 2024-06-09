
#include "hello_world.h"

void pss_top_init(
    pss_top_Entry_actor_t   *actor,
    pss_top_t               *obj) {
}

void pss_top_Sub_init(
    pss_top_Entry_actor_t   *actor,
    pss_top_Sub_t           *obj) {

}

void pss_top_Sub_exec_body_init(
    pss_top_Entry_actor_t       *actor,
    pss_top_Sub_exec_body_t     *obj) {

}

zsp_rt_task_t *pss_top_Sub_exec_body_run(
    pss_top_Entry_actor_t       *actor,
    pss_top_Sub_exec_body_t     *obj) {
    zsp_rt_task_t *ret = 0;

    switch (((zsp_rt_task_t *)obj)->idx) {
        case 0: {
            ((zsp_rt_task_t *)obj)->idx++;
            actor->funcs.print_f("Hello World!");
        }
        case 1: {
            ((zsp_rt_task_t *)obj)->idx++;
            ret = zsp_rt_task_return(
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
            body = (pss_top_Sub_exec_body_t *)zsp_rt_mblk_alloc(
                &((zsp_rt_actor_t *)actor)->stack_s,
                sizeof(pss_top_Sub_exec_body_t));
            pss_top_Sub_exec_body_init(actor, body);

            if ((ret=pss_top_Sub_exec_body_run(actor, body))) {
                break;
            }
        }

        case 1: {
            // We're done! Manage return
            ret = zsp_rt_task_return(
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
    zsp_rt_task_init(
        (zsp_rt_actor_t *)actor, 
        (zsp_rt_task_t *)obj,
        (zsp_rt_task_f)&pss_top_Entry_run);
    
    // Normally, we'd initialize plain-data fields, etc
}

zsp_rt_task_t *pss_top_Entry_run(
    pss_top_Entry_actor_t   *actor,
    pss_top_Entry_t         *obj) {
    zsp_rt_task_t *ret = 0;

    switch (((zsp_rt_task_t *)obj)->idx) {
        case 0: {
            pss_top_Sub_t *Sub_1;
            ((zsp_rt_task_t *)obj)->idx++;

            Sub_1 = (pss_top_Sub_t *)zsp_rt_mblk_alloc(
                &((zsp_rt_actor_t *)actor)->stack_s,
                sizeof(pss_top_Sub_t));

            pss_top_Sub_init(actor, Sub_1);

            if ((ret=pss_top_Sub_run(actor, Sub_1))) {
                break;
            }
        }
        case 1: {
            pss_top_Sub_t *Sub_2;
            ((zsp_rt_task_t *)obj)->idx++;

            Sub_2 = (pss_top_Sub_t *)zsp_rt_mblk_alloc(
                &((zsp_rt_actor_t *)actor)->stack_s,
                sizeof(pss_top_Sub_t));

            // Maybe want an atomic 'first call'?
            pss_top_Sub_init(actor, Sub_2);

            // TODO: Apply any post_init initialization
            // expressions here.

            if ((ret=pss_top_Sub_run(actor, Sub_2))) {
                break;
            }
        }
        case 2: {
            // All done. Tear down this stack frame 
            // and return the next task to run
            ret = zsp_rt_task_return(
                (zsp_rt_actor_t *)actor,
                (zsp_rt_task_t *)obj,
                0);
        }

    }

    return ret;
}

void pss_top_Entry_actor_init(pss_top_Entry_actor_t *actor) {

    zsp_rt_actor_init((zsp_rt_actor_t *)actor);

    // Initialize the component treej
    pss_top_init(actor, &actor->root_comp);

    // Create the root action and add it as a task

    // Configure the active task
}

int pss_top_Entry_actor_runOneTask(
    pss_top_Entry_actor_t   *actor) {

    return 0;
}

void pss_top_Entry_actor_run(
    pss_top_Entry_actor_t   *actor) {
    while (pss_top_Entry_actor_runOneTask(actor)) {
        ; 
    }
}


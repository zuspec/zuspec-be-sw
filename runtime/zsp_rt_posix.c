#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "zsp_rt.h"


int zsp_rt_run_one_task(
    zsp_rt_actor_t          *actor) {
    int ret = (actor->task_q)?1:0;

    if (actor->task_q) {
        zsp_rt_task_t *t = actor->task_q, *n;
        actor->task_q = t->next;
        n = zsp_rt_task_run(actor, t);
        if (n) {
            zsp_rt_queue_task(actor, n);
        }
    }

    return ret;
}

void zsp_rt_queue_task(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task) {
    
    if (!actor->task_q) {
        actor->task_q = task;
    } else {
        // Search to the end
        zsp_rt_task_t *p = actor->task_q;

        while (p->next) {
            p = p->next;
        }

        p->next = task;
        task->next = 0;
    }
}

zsp_rt_task_t *zsp_rt_task_enter(
    zsp_rt_actor_t          *actor,
    uint32_t                sz,
    zsp_rt_init_f           init_f) {
    // Capture incoming state so we can restore it later
    zsp_rt_mblk_t *prev_p = actor->stack_s;
    uint32_t prev_base = actor->stack_s->base;

    zsp_rt_task_t *task = (zsp_rt_task_t *)zsp_rt_mblk_alloc(
        &actor->stack_s, sz);
    
    // if (task == actor->task) {
    //     fprintf(stdout, "Circular ref\n");
    // }
    task->upper = actor->task;
    actor->task = task;

    task->stack_prev_p = prev_p;
    task->stack_prev_base = prev_base;
    task->next = 0;
    task->func = 0;
    task->idx = 0;

    init_f(actor, &task->rc);

    return task;
}

/*
zsp_rt_task_t *zsp_rt_task_run(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task) {
    zsp_rt_task_t *t;

    t = task->func(actor, task);
    return t;
}
 */

zsp_rt_task_t *zsp_rt_task_leave(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task,
    void                    *rval) {
    // Unwind the task stack
    zsp_rt_task_t *ret = task->upper;

    // Rewind the stack -- possibly freeing stack blocks
    while (actor->stack_s != task->stack_prev_p) {
        // TODO: release page
        break;
    }

    // Rewind the stack
    actor->stack_s = task->stack_prev_p; // TODO: temp
    actor->stack_s->base = task->stack_prev_base;
    actor->task = ret;

    // Determine the next task to run and return it
    /*
    if (ret) {
        ret = zsp_rt_task_run(actor, ret);
    } 
     */
    return ret;
}

void zsp_rt_actor_init(zsp_rt_actor_t *actor) {
    actor->stack_s = (zsp_rt_mblk_t *)malloc(
        sizeof(zsp_rt_mblk_t)+1024-sizeof(uint8_t)
    );
    memset(actor->stack_s, 0, sizeof(zsp_rt_mblk_t));
    actor->stack_r = actor->stack_s;

    actor->task = 0;
    actor->task_q = 0;
}

void zsp_rt_actor_mgr_init(zsp_rt_actor_mgr_t *mgr) {

}

void *zsp_rt_mblk_alloc(
    zsp_rt_mblk_t       **blk,
    uint32_t            sz) {
    void *ret;

    if (sz < 4) {
        sz= 4;
    }

    if (((*blk)->base+sz) > (*blk)->limit) {
        // Need a new block
    }

    ret = &(*blk)->mem[(*blk)->base];
    (*blk)->base += sz;

    return ret;
}

zsp_rt_addr_handle_t zsp_rt_addr_space_add_nonallocatable_region(
    zsp_rt_actor_t          *actor,
    zsp_rt_addr_space_t     *aspace,
    zsp_rt_addr_region_t    *region) {
    zsp_rt_addr_handle_t ret;
    // TODO: aspace must know
    // - sizeof(trait)
    // - whether opaque or transparent
    uint32_t sizeof_trait = sizeof(zsp_rt_rc_t);
    uint64_t addr = *((uint64_t *)((uint8_t *)region+sizeof(zsp_rt_addr_region_t)+sizeof_trait));
    zsp_rt_addr_claim_t *claim = (zsp_rt_addr_claim_t *)malloc(sizeof(zsp_rt_addr_claim_t));
    claim->hndl = (void *)addr;
    claim->store.actor = actor;
    claim->store.count = 0;
    fprintf(stdout, "addr: 0x%08llx\n", addr);
    ret.store = claim;
    ret.offset = 0;

    fprintf(stdout, "return hndl: 0x%p\n", ret.store->hndl);

    return ret;
}

void zsp_rt_reg_group_set_handle(zsp_rt_actor_t *actor, void **reg_h, zsp_rt_addr_handle_t *hndl) {
    fprintf(stdout, "get hndl: 0x%p\n", hndl->store->hndl);
    *reg_h = (void *)hndl->store->hndl;
}

#include <string.h>
#include <stdlib.h>
#include "zsp_rt.h"

void zsp_rt_task_init(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task,
    zsp_rt_task_f           run_f) {

}

zsp_rt_task_t *zsp_rt_task_return(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task,
    void                    *rval) {
    // The 'task'
    return 0;
}

void zsp_rt_actor_init(zsp_rt_actor_t *actor) {
    actor->stack_s = (zsp_rt_mblk_t *)malloc(
        sizeof(zsp_rt_mblk_t)+1024-sizeof(uint32_t)
    );
    memset(actor->stack_s, 0, sizeof(zsp_rt_mblk_t));
    actor->stack_r = actor->stack_s;
}

void *zsp_rt_mblk_alloc(
    zsp_rt_mblk_t       **blk,
    uint32_t            sz) {
    void *ret;

    if (((*blk)->base+sz) > (*blk)->limit) {
        // Need a new block
    }

    ret = &(*blk)->mem[(*blk)->base];
    (*blk)->base += sz;

    return ret;
}

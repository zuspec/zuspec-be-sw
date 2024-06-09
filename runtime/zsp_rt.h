/****************************************************************************
 * zsp_rt.h
 */
#ifndef INCLUDED_ZSP_RT_H
#define INCLUDED_ZSP_RT_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_rt_mblk_s {
    struct zsp_rt_mblk_s        *prev;
    uint32_t                    base;
    uint32_t                    limit;
    uint32_t                    mem[1];
} zsp_rt_mblk_t;

zsp_rt_mblk_t *zsp_rt_mblk_new(
    zsp_rt_mblk_t       *prev,
    uint32_t            sz);

void *zsp_rt_mblk_alloc(
    zsp_rt_mblk_t       **blk,
    uint32_t            sz);

void zsp_rt_mblk_free(
    zsp_rt_mblk_t       **blk,
    void                *p);

/*
void zsp_rt_mblk_rewind(
    zsp_rt_mblk_t           *prev,
    zsp_rt_mblk_t           *curr);
 */

typedef struct zsp_rt_actor_s {
    zsp_rt_mblk_t           *stack_r;
    zsp_rt_mblk_t           *stack_s;

} zsp_rt_actor_t;

typedef void (*zsp_rt_init_f)(zsp_rt_actor_t *, void *);

void zsp_rt_actor_init(zsp_rt_actor_t *actor);

struct zsp_rt_task_s;

typedef struct zsp_rt_task_s *(*zsp_rt_task_f)(
    zsp_rt_actor_t              *actor,
    struct zsp_rt_task_s        *task);

typedef struct zsp_rt_task_s {
    struct zsp_rt_task_s    *prev;
    zsp_rt_task_f           func;
    uint32_t                idx;
    zsp_rt_mblk_t           *stack_prev_p;
    zsp_rt_mblk_t           stack_prev;
} zsp_rt_task_t;

void zsp_rt_task_init(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task,
    zsp_rt_task_f           run_f);

zsp_rt_task_t *zsp_rt_task_return(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task,
    void                    *rval);

typedef struct zsp_rt_task_list_s {
    zsp_rt_task_t           task;
    uint32_t                n_tasks;
    uint32_t                n_done;
    zsp_rt_task_t           *tasks[1];
} zsp_rt_task_list_t;

typedef struct zsp_rt_action_s {
    zsp_rt_task_t           task;
} zsp_rt_action_t;

#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_RT_H */
/****************************************************************************
 * zsp_rt.h
 */
#ifndef INCLUDED_ZSP_RT_H
#define INCLUDED_ZSP_RT_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct zsp_rt_obj_s {
    int32_t                    size;
    int32_t                    refcnt;
    void (*dtor)(struct zsp_rt_obj_s *obj);
} zsp_rt_obj_t;

typedef struct addr_handle_s {
    zsp_rt_obj_t                obj;
} addr_handle_t;

typedef struct addr_claim_s {
    zsp_rt_obj_t                obj;
    int32_t                     sz;
} addr_claim_t;

typedef struct zsp_rt_mblk_s {
    struct zsp_rt_mblk_s        *prev;
    uint32_t                    base;
    uint32_t                    limit;
    uint8_t                     mem[1];
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
    struct zsp_rt_task_s    *task_q;
    struct zsp_rt_task_s    *task;
} zsp_rt_actor_t;

/**
 * Actor manager provides memory for all actors, and
 * coordinates their execution
 * 
 */
typedef struct zsp_rt_actor_mgr_s {

} zsp_rt_actor_mgr_t;

void zsp_rt_actor_mgr_init(zsp_rt_actor_mgr_t *mgr);

typedef void (*zsp_rt_init_f)(
    struct zsp_rt_actor_s *, 
    struct zsp_rt_task_s *);

void zsp_rt_actor_init(zsp_rt_actor_t *actor);

struct zsp_rt_task_s;

typedef struct zsp_rt_task_s *(*zsp_rt_task_f)(
    zsp_rt_actor_t              *actor,
    struct zsp_rt_task_s        *task);

typedef struct zsp_rt_task_s {
    struct zsp_rt_task_s    *upper;
    zsp_rt_task_f           func;
    uint32_t                idx;
    zsp_rt_mblk_t           *stack_prev_p;
    uint32_t                stack_prev_base;
    struct zsp_rt_task_s    *next;
} zsp_rt_task_t;

int zsp_rt_run_one_task(
    zsp_rt_actor_t          *actor);

void zsp_rt_queue_task(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task);

zsp_rt_task_t *zsp_rt_task_enter(
    struct zsp_rt_actor_s   *actor,
    uint32_t                sz,
    zsp_rt_init_f           init_f);

/*
zsp_rt_task_t *zsp_rt_task_run(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task);
 */
static inline zsp_rt_task_t *zsp_rt_task_run(
    zsp_rt_actor_t          *actor,
    zsp_rt_task_t           *task) {
    return task->func(actor, task);
}

zsp_rt_task_t *zsp_rt_task_leave(
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
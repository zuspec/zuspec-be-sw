/****************************************************************************
 * zsp_rt.h
 */
#ifndef INCLUDED_ZSP_RT_H
#define INCLUDED_ZSP_RT_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    false,
    true
} zsp_rt_bool_t;

struct zsp_rt_actor_s;

struct zsp_rt_rc_s;

typedef void (*zsp_rt_init_f)(
    struct zsp_rt_actor_s *, 
    struct zsp_rt_rc_s *);

typedef void (*zsp_rt_dtor_f)(
    struct zsp_rt_actor_s *,
    struct zsp_rt_rc_s *);

typedef struct zsp_rt_rc_s {
    zsp_rt_dtor_f           dtor;
    uint32_t                count;
    struct zsp_rt_actor_s   *actor;
    uint8_t                 store[1];
} zsp_rt_rc_t;

zsp_rt_rc_t *zsp_rt_rc_new(
    struct zsp_rt_actor_s   *actor,
    uint32_t                sz,
    zsp_rt_init_f           init);

void zsp_rt_rc_dtor(
    struct zsp_rt_actor_s   *actor,
    zsp_rt_rc_t             *rc);

#define zsp_rt_addr_handle_acq(hndl) \
    ((hndl).store && (hndl).store->count++)?hndl:hndl;

#define zsp_rt_rc_dec(rc) \
    if ((zsp_rt_rc_t *)(rc) && ((zsp_rt_rc_t *)(rc))->count && !(--(((zsp_rt_rc_t *)(rc))->count))) { \
        ((zsp_rt_rc_t *)(rc))->dtor( \
            ((zsp_rt_rc_t *)(rc))->actor, \
            ((zsp_rt_rc_t *)(rc))); \
    }
// #define zsp_rt_rc_dec(rc) \
//     if (((zsp_rt_rc_t *)(rc))->count && !(--(((zsp_rt_rc_t *)(rc))->count))) { \
//         fprintf(stdout, "dtor dtor=%p\n", \
//             ((zsp_rt_rc_t *)(rc))->dtor); \
//         ((zsp_rt_rc_t *)(rc))->dtor(0, 0); \
//     }
#define zsp_rt_rc_inc(rc) ((zsp_rt_rc_t *)(rc))->count++;

typedef struct zsp_rt_obj_s {
    int32_t                    size;
    int32_t                    refcnt;
    void (*dtor)(struct zsp_rt_obj_s *obj);
} zsp_rt_obj_t;

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

struct zsp_rt_actor_impl_s;
typedef struct zsp_rt_actor_s {
    struct zsp_rt_actor_impl_s  *impl;
    zsp_rt_mblk_t               *stack_r;
    zsp_rt_mblk_t               *stack_s;
    struct zsp_rt_task_s        *task_q;
    struct zsp_rt_task_s        *task;
    uint64_t                    seed;
} zsp_rt_actor_t;

/**
 * Actor manager provides memory for all actors, and
 * coordinates their execution
 * 
 */
typedef struct zsp_rt_actor_mgr_s {

} zsp_rt_actor_mgr_t;

void zsp_rt_actor_mgr_init(zsp_rt_actor_mgr_t *mgr);


void zsp_rt_actor_init(zsp_rt_actor_t *actor);

struct zsp_rt_task_s;

typedef struct zsp_rt_task_s *(*zsp_rt_task_f)(
    zsp_rt_actor_t              *actor,
    struct zsp_rt_task_s        *task);

typedef struct zsp_rt_task_s {
    zsp_rt_rc_t             rc;
    struct zsp_rt_task_s    *upper;
    zsp_rt_task_f           func;
    uint32_t                idx;
    zsp_rt_mblk_t           *stack_prev_p;
    uint32_t                stack_prev_base;
    struct zsp_rt_task_s    *prev;
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
    zsp_rt_task_t *task_n = task->func(actor, task);
    if (task_n && task != task_n) {
        // Allow the caller
        task_n->prev = task;
    } else if (task->upper) {
        task->upper->prev = task;
    }

    return task_n;
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

typedef struct zsp_rt_component_s {
    zsp_rt_obj_t            obj;
    int32_t                 comp_id;
} zsp_rt_component_t;

typedef struct zsp_rt_addr_claim_s {
    zsp_rt_rc_t     store;
    uint8_t         *hndl;
} zsp_rt_addr_claim_t;

typedef struct zsp_rt_addr_claimspec_s {
    zsp_rt_rc_t             base;
    zsp_rt_addr_claim_t     *claim;
} zsp_rt_addr_claimspec_t;

typedef struct zsp_rt_addr_handle_s {
    zsp_rt_addr_claim_t     *store;
    uint64_t                offset;
} zsp_rt_addr_handle_t;

struct zsp_rt_addr_handle_s zsp_rt_make_handle_from_handle(
    zsp_rt_actor_t          *actor,
    zsp_rt_addr_handle_t    *handle,
    uint64_t                offset);

struct zsp_rt_addr_handle_s zsp_rt_make_handle_from_claim(
    zsp_rt_actor_t          *actor,
    zsp_rt_addr_claimspec_t *claim,
    uint64_t                offset);

uintptr_t zsp_rt_addr_value(zsp_rt_addr_handle_t *handle);


typedef struct zsp_rt_addr_region_s {
    zsp_rt_rc_t         base;
    uint64_t            size;
} zsp_rt_addr_region_t;

struct zsp_rt_addr_space_impl_s;
typedef struct zsp_rt_addr_space_s {
    struct zsp_rt_addr_space_impl_s     *impl;
} zsp_rt_addr_space_t;

typedef int (*zsp_rt_claimspec_match_f)(
    void                    *ud,
    zsp_rt_addr_region_t    *region);

void zsp_rt_alloc_claim(
    zsp_rt_actor_t              *actor,
    zsp_rt_addr_space_t         *aspace,
    zsp_rt_addr_claimspec_t     *claim,
    zsp_rt_claimspec_match_f    *match_f,
    void                        *match_ud
);

zsp_rt_addr_claim_t *zsp_rt_addr_claim_new(
    zsp_rt_actor_t              *actor);

void zsp_rt_addr_space_init(
    zsp_rt_actor_t          *actor,
    zsp_rt_addr_space_t     *aspace,
    int32_t                 trait_sz);

zsp_rt_addr_handle_t zsp_rt_addr_space_add_nonallocatable_region(
    zsp_rt_actor_t          *actor,
    zsp_rt_addr_space_t     *aspace,
    zsp_rt_addr_region_t    *region);

zsp_rt_addr_handle_t zsp_rt_addr_space_add_region(
    zsp_rt_actor_t          *actor,
    zsp_rt_addr_space_t     *aspace,
    zsp_rt_addr_region_t    *region);

void zsp_rt_reg_group_set_handle(zsp_rt_actor_t *actor, void **reg_h, zsp_rt_addr_handle_t *hndl);



#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_RT_H */
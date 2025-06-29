#ifndef INCLUDED_ZSP_THREAD_H
#define INCLUDED_ZSP_THREAD_H

#include <stdint.h>
#include <stdarg.h>
#include "zsp_alloc.h"

#ifdef __cplusplus
extern "C" {
#endif

#define STACK_FRAME_SZ 4096
#define STACK_FRAME_MAX (STACK_FRAME_SZ-(sizeof(frame_t *)+sizeof(uint32_t)))

struct zsp_thread_s; 

typedef struct zsp_frame_s *(*zsp_task_func)(struct zsp_thread_s *, int idx, va_list *args);

typedef enum {
  ZSP_THREAD_FLAGS_NONE = 0,
  ZSP_THREAD_FLAGS_SUSPEND = 0x1,
  ZSP_THREAD_FLAGS_BLOCKED = 0x2
} zsp_thread_flags_e;


typedef struct zsp_frame_s {
    zsp_task_func       func;
    struct zsp_frame_s  *prev;
    zsp_thread_flags_e  flags;
    int32_t             idx;
} zsp_frame_t;

typedef struct zsp_frame_wrap_s {
    zsp_frame_t         frame;
    uintptr_t           locals;
} zsp_frame_wrap_t;

#define zsp_frame_size(t) \
    sizeof(struct {zsp_frame_t __f; t __locals;})

#define zsp_thread_clear_flags(thread, f) \
    ((zsp_thread_t *)(thread))->flags &= ~(f)

typedef struct zsp_stack_block_s {
    struct zsp_stack_block_s    *prev;
    uintptr_t                   limit;
    uintptr_t                   base;
//    uint32_t                    idx;
//    uint32_t                    sz;
//    uint8_t                     data[
//        STACK_FRAME_SZ-(sizeof(zsp_frame_t *)+sizeof(uint32_t))];
} zsp_stack_block_t;

struct zsp_thread_group_s;

typedef struct zsp_prev_next_s {
    struct zsp_prev_next_s *prev;
    struct zsp_prev_next_s *next;
} zsp_prev_next_t;

typedef void (*zsp_thread_group_event_f)(
    struct zsp_thread_group_s   *group, 
    struct zsp_thread_s         *thread);

typedef struct zsp_thread_group_methods_s {
    zsp_thread_group_event_f    enter;
    zsp_thread_group_event_f    leave;
} zsp_thread_group_methods_t;

typedef struct zsp_thread_group_s {
    zsp_prev_next_t             base;
    struct zsp_thread_group_s   *parent;
    zsp_thread_group_methods_t  *funcs;
} zsp_thread_group_t;

typedef void (*zsp_thread_exit_f)(struct zsp_thread_s *);


typedef struct zsp_thread_s {
    // If this thread is part of a group, then
    zsp_prev_next_t             group;
    zsp_thread_exit_f           exit_f;
    struct zsp_frame_s          *leaf;

    zsp_alloc_t                 alloc; // Allocator for thread-local storage

    // Allocator for thread-local storage
    zsp_stack_block_t           *block;

    // sched handle is valid when thread is executing
    union {
        struct zsp_thread_s     *next;
        struct zsp_scheduler_s  *sched;
    };

    uintptr_t                   rval;
    zsp_thread_flags_e          flags;
} zsp_thread_t;

typedef struct zsp_scheduler_s {
    zsp_alloc_t        *alloc;
    zsp_thread_t       *next;
    zsp_thread_t       *tail;
    int32_t            active;
} zsp_scheduler_t;

#define zsp_thread_clear_flags_transient(thread) \
    ((zsp_thread_t *)(thread))->flags &= ~(ZSP_THREAD_FLAGS_SUSPEND)

void zsp_scheduler_init(zsp_scheduler_t *sched, zsp_alloc_t *alloc);

zsp_scheduler_t *zsp_scheduler_create(zsp_alloc_t *alloc);

void zsp_thread_schedule(zsp_scheduler_t *sched, zsp_thread_t *thread);

// zsp_thread_t *zsp_scheduler_create_thread(
//     zsp_scheduler_t *sched, 
//     zsp_task_func func, 
//     zsp_thread_flags_e flags, ...);

// void zsp_scheduler_thread_init(
//     zsp_scheduler_t *sched, 
//     zsp_thread_t *thread, 
//     zsp_task_func func, 
//     zsp_thread_flags_e flags, 
//     ...);

int zsp_scheduler_run(zsp_scheduler_t *sched);

zsp_thread_t *zsp_thread_create(
    zsp_scheduler_t     *sched, 
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...);

zsp_thread_t *zsp_thread_init(
    zsp_scheduler_t     *sched, 
    zsp_thread_t        *thread,
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...);

zsp_thread_t *zsp_thread_create_group(
    zsp_scheduler_t     *sched, 
    zsp_thread_group_t  *group,
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...);
    
zsp_thread_t *zsp_thread_init_group(
    zsp_thread_t        *thread,
    zsp_scheduler_t     *sched, 
    zsp_thread_group_t  *group,
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...);

void zsp_thread_group_init(
    zsp_thread_group_t          *group, 
    zsp_thread_group_t          *parent, 
    zsp_thread_group_methods_t *funcs);

struct zsp_frame_s *zsp_thread_group_join(
    zsp_thread_group_t *group,
    struct zsp_thread_s *thread);

#define zsp_frame_locals(frame, locals_t) \
    ((locals_t *)&((zsp_frame_wrap_t *)(frame))->locals)

zsp_frame_t *zsp_thread_alloc_frame(zsp_thread_t *thread, uint32_t sz, zsp_task_func func);
void *zsp_thread_alloca(zsp_thread_t *thread, size_t sz);
void zsp_thread_yield(zsp_thread_t *thread);

// Used by tasks to manage scope-local storage
uintptr_t zsp_thread_getsp(zsp_thread_t *thread);
uintptr_t zsp_thread_setsp(zsp_thread_t *thread, uintptr_t sp);

zsp_frame_t *zsp_thread_return(zsp_thread_t *thread, uintptr_t ret);
struct zsp_scheduler_s *zsp_thread_scheduler(zsp_thread_t *thread);
zsp_frame_t *zsp_thread_call(zsp_thread_t *thread, zsp_task_func func, ...);
zsp_frame_t *zsp_thread_call_id(zsp_thread_t *thread, int32_t idx, zsp_task_func func, ...);
uintptr_t zsp_thread_va_arg(va_list *args, size_t sz);
// zsp_frame_t *zsp_thread_run(zsp_thread_t *thread);
void zsp_thread_free(zsp_thread_t *thread);



#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_THREAD_H */


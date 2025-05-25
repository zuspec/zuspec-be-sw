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

typedef struct zsp_frame_s *(*zsp_task_func)(struct zsp_thread_s *, struct zsp_frame_s *, va_list *args);

typedef struct zsp_frame_s {
    zsp_task_func       func;
    struct zsp_frame_s  *prev;
    uint32_t            sz;
    int32_t             idx;
} zsp_frame_t;

typedef struct zsp_frame_wrap_s {
    zsp_frame_t         frame;
    uintptr_t           locals;
} frame_wrap_t;

typedef struct zsp_stack_block_s {
    struct zsp_stack_block_s    *prev;
    uint32_t                    idx;
    uint32_t                    sz;
    uint8_t                     data[
        STACK_FRAME_SZ-(sizeof(zsp_frame_t *)+sizeof(uint32_t))];
} zsp_stack_block_t;

typedef struct zsp_thread_s {
    zsp_alloc_t         *alloc;
    zsp_stack_block_t   *block;
    struct zsp_thread_s *next;
    struct zsp_frame_s  *leaf;
    uintptr_t           rval;
} zsp_thread_t;

typedef struct zsp_scheduler_s {
    zsp_alloc_t        *alloc;
    zsp_thread_t       *next;
    zsp_thread_t       *tail;
} zsp_scheduler_t;

void zsp_scheduler_init(zsp_scheduler_t *sched, zsp_alloc_t *alloc);
zsp_thread_t *zsp_scheduler_create_thread(zsp_scheduler_t *sched, zsp_task_func func, ...);
int zsp_scheduler_run(zsp_scheduler_t *sched);
zsp_thread_t *zsp_thread_create(zsp_alloc_t *alloc, zsp_task_func func, ...);
zsp_frame_t *zsp_thread_alloc_frame( zsp_thread_t *thread, uint32_t sz, zsp_task_func func);
zsp_frame_t *zsp_thread_suspend(zsp_thread_t *thread, zsp_frame_t *frame);
zsp_frame_t *zsp_thread_return(zsp_thread_t *thread, zsp_frame_t *frame, uintptr_t ret);
zsp_frame_t *zsp_thread_call(zsp_thread_t *thread, zsp_task_func func, ...);
zsp_frame_t *zsp_thread_run(zsp_thread_t *thread);
void zsp_thread_free(zsp_thread_t *thread);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_THREAD_H */


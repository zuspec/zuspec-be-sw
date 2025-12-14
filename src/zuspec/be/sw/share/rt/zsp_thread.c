
#include <stddef.h>
#include <stdio.h>
#include "zsp_thread.h"


void zsp_thread_queue_init(zsp_thread_queue_t *q) {
    q->head = 0;
    q->tail = 0;
}

void zsp_thread_queue_add(zsp_thread_queue_t *q, zsp_thread_t *t) {
    t->next = 0;
    if (q->head) {
        q->tail->next = t;
        q->tail = t;
    } else {
        q->head = t;
        q->tail = t;
    }
}

zsp_thread_t *zsp_thread_queue_pop(zsp_thread_queue_t *q) {
    zsp_thread_t *ret = q->head;
    if (q->head) {
        q->head = q->head->next;
        if (!q->head) {
            q->tail = 0;
        }
    }
    return ret;
}

void zsp_scheduler_init(zsp_scheduler_t *sched, zsp_alloc_t *alloc) {
    sched->alloc = alloc;
    zsp_thread_queue_init(&sched->queue);
    sched->active = 0;
}

zsp_scheduler_t *zsp_scheduler_create(zsp_alloc_t *alloc) {
    zsp_scheduler_t *sched = (zsp_scheduler_t *)alloc->alloc(alloc, sizeof(zsp_scheduler_t));
    zsp_scheduler_init(sched, alloc);
    return sched;
}

void zsp_thread_schedule(zsp_scheduler_t *sched, zsp_thread_t *thread) {
    sched->active++;
//    fprintf(stdout, "[sched] Scheduling thread: %p (%d)\n", thread, sched->active);
//    fflush(stdout);
    thread->flags &= ~ZSP_THREAD_FLAGS_BLOCKED;
    zsp_thread_queue_add(&sched->queue, thread);
}

void zsp_scheduler_init_threadv(
    zsp_scheduler_t *sched, 
    zsp_thread_t *thread, 
    zsp_task_func func, 
    zsp_thread_flags_e flags,
    va_list *args) {

//    fprintf(stdout, "[sched] init_threadv: %p\n", thread);
//    fflush(stdout);

    thread->exit_f = 0;
    thread->block = 0;
    thread->leaf = 0;
    thread->next = 0;
    thread->sched = sched;
    thread->flags = (flags | ZSP_THREAD_FLAGS_INITIAL);
    zsp_frame_t *ret;

    ret = func(thread, 0, args);

    thread->leaf = ret;
    thread->flags &= ~ZSP_THREAD_FLAGS_INITIAL;

    if (ret && (thread->flags & ZSP_THREAD_FLAGS_SUSPEND) != 0) {
        // Reschedule the thread
        zsp_thread_schedule(sched, thread);
    } else {
        thread->flags |= ZSP_THREAD_FLAGS_BLOCKED;
        thread->next = 0;
    }
}

// void zsp_scheduler_thread_init(
//     zsp_scheduler_t     *sched, 
//     zsp_thread_t        *thread, 
//     zsp_task_func       func, 
//     zsp_thread_flags_e  flags,
//     ...) {
//     va_list args;
//     va_start(args, flags);

//     zsp_scheduler_init_threadv(sched, thread, func, flags, &args);

//     va_end(args);
// }

// zsp_thread_t *zsp_scheduler_create_thread(
//     zsp_scheduler_t     *sched, 
//     zsp_task_func       func, 
//     zsp_thread_flags_e  flags,
//     ...) {
//     va_list args;
//     va_start(args, flags);
//     zsp_thread_t *thread = (zsp_thread_t *)sched->alloc->alloc(
//         sched->alloc, sizeof(zsp_thread_t));
   
//     zsp_scheduler_init_threadv(sched, thread, func, flags, &args);

//     return thread;
// }

int zsp_scheduler_run(zsp_scheduler_t *sched) {
    // TODO: Mutex this
    jmp_buf env;
    zsp_thread_t *thread = zsp_thread_queue_pop(&sched->queue);

    if (thread) {
        sched->active--;

        // The scheduler is the last thing to see a thread before it ends.
        // We may be handling an already-completed thread
        if (thread->leaf) {
            thread->sched = sched;
            if (setjmp(env)) {
                // TODO: Exception
            } else {
                sched->env_p = &env;
                thread->leaf = thread->leaf->func(
                    thread,
                    thread->leaf->idx,
                    0);
            }
        }

        // TODO: Should only add back to the queue if not blocked.
        // Threads that yield are added back, such that they will 
        // be automatically resumed
        if (thread->leaf) {
            if ((thread->flags & ZSP_THREAD_FLAGS_SUSPEND) != 0) {
                // Thread was suspended. Reinsert
                thread->flags &= ~ZSP_THREAD_FLAGS_SUSPEND;

                // TODO: Mutex this
                zsp_thread_schedule(sched, thread);
            } else {
                // Thread is blocked. Clear 'next' to ensure that we
                // know it is not scheduled
                thread->flags |= ZSP_THREAD_FLAGS_BLOCKED;
                thread->next = 0;
            }
        } else {
            // Thread is complete
            if (thread->exit_f) {
                thread->exit_f(thread);
            }
        }
    }

    // More threads to run
    return (sched->next)?1:0;
}

static void *__zsp_thread_alloc(zsp_alloc_t *alloc, size_t sz) {
    zsp_thread_t *thread = (zsp_thread_t *)(
        ((uintptr_t)alloc)-(offsetof(struct zsp_thread_s, alloc)));
    return zsp_thread_alloca(thread, sz);
}

void __zsp_thread_init(
    zsp_thread_t        *thread, 
    zsp_scheduler_t     *sched,
    zsp_thread_flags_e  flags) {

//    fprintf(stdout, "[sched] __zsp_thread_init: %p\n", thread);
//    fflush(stdout);

    thread->exit_f = 0;
    thread->block = 0;
    thread->leaf = 0;

    // Thread-local alloc is freed when the stack is popped
    thread->alloc.alloc = __zsp_thread_alloc;
    thread->alloc.free = 0; 
    thread->sched = sched;
    thread->flags = flags;

}

zsp_thread_t *zsp_thread_init(
    zsp_scheduler_t     *sched, 
    zsp_thread_t        *thread,
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...) {
    va_list args;
    va_start(args, flags);
    __zsp_thread_init(thread, sched, flags);
    // TODO: new thread dictates new thread-specific allocator
//    new_thread->alloc = thread->alloc;
    zsp_frame_t *ret;

    ret = func(thread, 0, &args);
    va_end(args);


//    // Clean up automatically, so the thread doesn't need to do this
//    zsp_thread_clear_flags(thread, ZSP_THREAD_FLAGS_SUSPEND);

    thread->leaf = ret;

    thread->flags &= ~ZSP_THREAD_FLAGS_INITIAL;

    if (ret && (thread->flags & ZSP_THREAD_FLAGS_SUSPEND) != 0) {
        // Schedule the thread
        thread->flags &= ~ZSP_THREAD_FLAGS_SUSPEND;
        zsp_thread_schedule(sched, thread);
    } else {
        thread->next = 0;
        thread->flags |= ZSP_THREAD_FLAGS_BLOCKED;
    }

    return thread;
}

// static struct zsp_frame_s *__zsp_thread_group_join_task(
//     zsp_thread_t *thread, int idx, va_list *args) {
//     zsp_frame_t *ret = thread->leaf;
//     typedef struct __locals_s {
//         zsp_thread_group_t *group;
//     } __locals_t;

//     switch (idx) {
//         case 0: {
//             zsp_thread_group_t *group = va_arg(*args, zsp_thread_group_t *);
//             __locals_t *__locals;

//             ret = zsp_thread_alloc_frame(
//                 thread, 
//                 sizeof(__locals_t),
//                 &__zsp_thread_group_join_task);

//             __locals = zsp_frame_locals(ret, __locals_t);
//             __locals->group = group;
// }

struct zsp_frame_s *zsp_thread_group_join(
    zsp_thread_group_t *group,
    struct zsp_thread_s *thread) {
    if (group->base.next) {

    }
    return 0;
}

zsp_thread_t *zsp_thread_create(
    zsp_scheduler_t     *sched, 
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...) {
    va_list args;
    va_start(args, flags);
    zsp_thread_t *thread = (zsp_thread_t *)sched->alloc->alloc(
        sched->alloc, sizeof(zsp_thread_t));

    thread->group = (zsp_prev_next_t){0, 0};
    thread->block = 0;
    thread->leaf = 0;
    thread->sched = sched;
    thread->exit_f = 0;
    thread->flags = (flags | ZSP_THREAD_FLAGS_INITIAL);
    zsp_frame_t *ret;

    ret = func(thread, 0, &args);
    va_end(args);

    thread->leaf = ret;
    thread->flags &= ~ZSP_THREAD_FLAGS_INITIAL;

    if (ret && (thread->flags & ZSP_THREAD_FLAGS_SUSPEND) != 0) {
        // Clean up automatically, so the thread doesn't need to do this
        zsp_thread_clear_flags(thread, ZSP_THREAD_FLAGS_SUSPEND);

        // Schedule the thread
        zsp_thread_schedule(sched, thread);
    }

    return thread;
}

void zsp_thread_free(zsp_thread_t *thread) {
    if (thread->block) {
        thread->sched->alloc->free(thread->sched->alloc, thread->block);
    }
    thread->sched->alloc->free(thread->sched->alloc, thread);
}

zsp_frame_t *zsp_thread_alloc_frame(
    zsp_thread_t    *thread, 
    uint32_t        sz,
    zsp_task_func   func) {
    zsp_frame_t *ret;

    sz = sz ? sz : sizeof(uintptr_t);

    uint32_t total_sz = sizeof(zsp_frame_t) + sz;
    if (!thread->block || ((thread->block->base+total_sz) >= thread->block->limit)) {
        uint32_t block_sz = 8192; // TODO:
        zsp_stack_block_t *block = (zsp_stack_block_t *)
            thread->sched->alloc->alloc(
                thread->sched->alloc, 
                (sizeof(zsp_stack_block_t)+block_sz));
        block->base = (uintptr_t)&block->base+sizeof(uintptr_t);
        block->limit = block->base+block_sz-1;

//        fprintf(stdout, "[alloc_frame] Allocating new block: %p base=%p limit=%p exp=%p\n", 
//            block, block->base, block->limit,
//            ((uintptr_t)block)+(sizeof(zsp_stack_block_t)+block_sz));

        block->prev = thread->block;
        thread->block = block;
    }

    ret = (zsp_frame_t *)thread->block->base;
    thread->block->base += total_sz;
    // fprintf(stdout, "[alloc_frame] %p..%p %d %d base=%p limit=%p exp=%p\n", 
    //     ret, ((uintptr_t)ret)+total_sz,
    //     sizeof(zsp_frame_t), sz,
    //     thread->block->base, thread->block->limit,
    //     (thread->block->base+total_sz));

    ret->func = func;
    ret->prev = thread->leaf;
    ret->idx = 0;
    thread->leaf = ret;

    return ret;
}

void *zsp_thread_alloca(
    zsp_thread_t    *thread, 
    size_t          sz) {
    void *ret;

    uint32_t total_sz = sz;
    if (!thread->block || (thread->block->base+total_sz) >= thread->block->limit) {
        zsp_stack_block_t *block = (zsp_stack_block_t *)
            thread->sched->alloc->alloc(thread->sched->alloc, sizeof(zsp_stack_block_t));
        // TODO: need to select the block size more intelligently
        uint32_t block_sz = 4096; // TODO: 

//        fprintf(stdout, "[alloca] Allocating new block: %p\n", block);

        block->base = (uintptr_t)&block->base+sizeof(uintptr_t);
        block->limit = block->base+block_sz-1;

        block->prev = thread->block;
        thread->block = block;
//        fprintf(stdout, "New block: %p\n", thread->block);
    }

    ret = (void *)thread->block->base;
    thread->block->base += total_sz;

    return ret;
}

zsp_frame_t *zsp_thread_call(zsp_thread_t *thread, zsp_task_func func, ...) {
    va_list args;
    va_start(args, func);
    zsp_frame_t *ret;

    ret = func(thread, 0, &args);

    va_end(args);

    return ret;
}

zsp_frame_t *zsp_thread_call_id(zsp_thread_t *thread, int32_t idx, zsp_task_func func, ...) {
    va_list args;
    va_start(args, func);
    zsp_frame_t *ret;

    ret = func(thread, idx, &args);

    va_end(args);

    return ret;
}

uintptr_t zsp_thread_va_arg(va_list *args, size_t sz) {
    uintptr_t ret;
    switch (sz) {
        case 1: {
            ret = (uintptr_t)va_arg(*args, uint8_t);
            break;
        }
        case 2: {
            ret = (uintptr_t)va_arg(*args, uint16_t);
            break;
        }
        case 4: {
            ret = (uintptr_t)va_arg(*args, uint32_t);
            break;
        }
        case 8: {
            ret = (uintptr_t)va_arg(*args, uint64_t);
            break;
        }
        default: {
            fprintf(stderr, "Unsupported size for va_arg: %zu\n", sz);
            ret = 0;
            break;
        }
        }
    
    return ret;
};

void zsp_thread_yield(zsp_thread_t *thread) {
    thread->flags |= ZSP_THREAD_FLAGS_SUSPEND;
}

void zsp_thread_block(zsp_thread_t *thread) {
    thread->flags |= ZSP_THREAD_FLAGS_BLOCKED;
}

uintptr_t zsp_thread_getsp(zsp_thread_t *thread) {
    return thread->block->base;
}

uintptr_t zsp_thread_setsp(zsp_thread_t *thread, uintptr_t sp) {
    if (sp && thread->block->base != sp) {
        // First, remove blocks until we find the one containing the frame
        while (thread->block) {
            if (sp >= (uintptr_t)thread->block && sp <= thread->block->limit) {
                break;
            } else {
                zsp_stack_block_t *prev = thread->block->prev;
                thread->sched->alloc->free(thread->sched->alloc, thread->block);
                fprintf(stdout, "[return] Freeing block: %p\n", thread->block);
                thread->block = prev;
            }
        }
        thread->block->base = sp;
    }
    return thread->block->base;
}

zsp_frame_t *zsp_thread_return(zsp_thread_t *thread, uintptr_t rval) {
    zsp_frame_t *ret = thread->leaf;
    uintptr_t frame_v = (uintptr_t)ret;
    thread->rval = rval;

    // First, remove blocks until we find the one containing the frame
    while (thread->block) {
        if (frame_v >= (uintptr_t)thread->block && frame_v <= thread->block->limit) {
            break;
        } else {
            zsp_stack_block_t *prev = thread->block->prev;
            thread->sched->alloc->free(thread->sched->alloc, thread->block);
            fprintf(stdout, "[return] Freeing block: %p\n", thread->block);
            thread->block = prev;
        }
    }

    // Roll back the 'base' pointer to the previous frame
    if (thread->block) {
        thread->block->base = (uintptr_t)ret;
    }

    // Note: frame is null if we've finished unwinding the stack
    if (ret) {
        zsp_frame_t *prev = ret->prev;

        thread->leaf = prev;
        ret = prev;
        if ((thread->flags & ZSP_THREAD_FLAGS_INITIAL) != 0) {
            ret = 0;
        } else {
            if (prev && !(thread->flags & ZSP_THREAD_FLAGS_BLOCKED)) {
                // Unblock the frame before calling
                thread->flags &= ~ZSP_THREAD_FLAGS_SUSPEND;
                ret = prev->func(thread, prev->idx, 0);
                thread->leaf = ret;
            }
        } 
    }

    return ret;
}

struct zsp_scheduler_s *zsp_thread_scheduler(zsp_thread_t *thread) {
    return thread->sched;
}

zsp_frame_t *zsp_thread_run(zsp_thread_t *thread) {
    if (thread->leaf) {
        thread->leaf = thread->leaf->func(thread, thread->leaf->idx, 0);
    }    

    return thread->leaf;
}

static zsp_frame_t *zsp_thread_group_join_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    typedef struct __locals_s {
        zsp_thread_group_t *group;
    } __locals_t;

    switch (idx) {
        case 0: {
            zsp_thread_group_t *group = va_arg(*args, zsp_thread_group_t *);
            __locals_t *__locals;

            ret = zsp_thread_alloc_frame(
                thread, 
                sizeof(__locals_t),
                &zsp_thread_group_join_task);

            __locals = zsp_frame_locals(ret, __locals_t);
            __locals->group = group;

            // TOOD: Intercept the 'thread-complete' function so we can
            // tell when all the threads of interest have completed

            // Wait un the 'all-done' event
        }

        default: {
            ret = zsp_thread_return(thread, 0);
        }
    }

    return ret;
}

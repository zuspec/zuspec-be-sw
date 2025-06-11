
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_thread.h"

void zsp_scheduler_init(zsp_scheduler_t *sched, zsp_alloc_t *alloc) {
    sched->alloc = alloc;
    sched->next = 0;
    sched->tail = 0;
}

void zsp_scheduler_init_threadv(
    zsp_scheduler_t *sched, 
    zsp_thread_t *thread, 
    zsp_task_func func, 
    zsp_thread_flags_e flags,
    va_list *args) {

    thread->block = 0;
    thread->leaf = 0;
    thread->next = 0;
    thread->sched = sched;
    thread->flags = flags;
    zsp_frame_t *ret;

    ret = func(thread, 0, args);

    thread->leaf = ret;

    if (sched->next) {
        sched->tail->next = thread;
        sched->tail = thread;
        // zsp_thread_t *t = sched->next;
        // // Find the end of the list
        // while (t && t->next) {
        //     t = t->next;
        // }
        // t->next = thread;
    } else {
        sched->next = thread;
        sched->tail = thread;
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
    zsp_thread_t *thread = sched->next;
    if (sched->next) {
        sched->next = sched->next->next;
        if (!sched->next) {
            sched->tail = 0;
        }
    }

    if (thread) {
        thread->sched = sched;
        thread->leaf = thread->leaf->func(
            thread,
            thread->leaf, 
            0);
        
        if (thread->leaf) {
            // Insert into the scheduler
            // TODO: Mutex this
            thread->next = 0;
            if (sched->next) {
                sched->tail->next = thread;
                sched->tail = thread;
                // zsp_thread_t *t = sched->next;
                // // Find the end of the list
                // while (t->next) {
                //     t = t->next;
                // }
                // t->next = thread;
            } else {
                sched->next = thread;
                sched->tail = thread;
            }
        }
    }

    // More threads to run
    return (sched->next)?1:0;
}

zsp_thread_t *zsp_thread_init(
    zsp_scheduler_t     *sched, 
    zsp_thread_t        *thread,
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...) {
    va_list args;
    va_start(args, flags);
    thread->block = 0;
    thread->leaf = 0;
    thread->sched = sched;
    thread->flags = flags;
    // TODO: new thread dictates new thread-specific allocator
//    new_thread->alloc = thread->alloc;
    zsp_frame_t *ret;

    ret = func(thread, 0, &args);
    va_end(args);

    // Clean up automatically, so the thread doesn't need to do this
    zsp_thread_clear_flags(thread, ZSP_THREAD_FLAGS_SUSPEND);

    thread->leaf = ret;

    if (ret && !(thread->flags & ZSP_THREAD_FLAGS_BLOCKED)) {
        // Schedule the thread
        thread->next = 0;
        if (sched->next) {
            sched->tail->next = thread;
            sched->tail = thread;
        } else {
            sched->next = thread;
            sched->tail = thread;
        }
    }

    return thread;
}

zsp_thread_t *zsp_thread_create(
    zsp_scheduler_t     *sched, 
    zsp_task_func       func, 
    zsp_thread_flags_e  flags, ...) {
    va_list args;
    va_start(args, flags);
    zsp_thread_t *thread = (zsp_thread_t *)sched->alloc->alloc(
        sched->alloc, sizeof(zsp_thread_t));
    thread->block = 0;
    thread->leaf = 0;
    thread->sched = sched;
    thread->flags = flags;
    // TODO: new thread dictates new thread-specific allocator
//    new_thread->alloc = thread->alloc;
    zsp_frame_t *ret;

    ret = func(thread, 0, &args);
    va_end(args);

    // Clean up automatically, so the thread doesn't need to do this
    zsp_thread_clear_flags(thread, ZSP_THREAD_FLAGS_SUSPEND);

    thread->leaf = ret;

    if (ret && !(thread->flags & ZSP_THREAD_FLAGS_BLOCKED)) {
        // Schedule the thread
        thread->next = 0;
        if (sched->next) {
            sched->tail->next = thread;
            sched->tail = thread;
        } else {
            sched->next = thread;
            sched->tail = thread;
        }
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

    uint32_t total_sz = sizeof(zsp_frame_t) + sz;
    if (!thread->block || ((thread->block->base+total_sz) >= thread->block->limit)) {
        uint32_t block_sz = 4096; // TODO:
        zsp_stack_block_t *block = (zsp_stack_block_t *)
            thread->sched->alloc->alloc(
                thread->sched->alloc, 
                (sizeof(zsp_stack_block_t)+block_sz));
        block->base = (uintptr_t)&block->base+sizeof(uintptr_t);
        block->limit = block->base+block_sz-1;

        block->prev = thread->block;
        thread->block = block;
    }

    ret = (zsp_frame_t *)thread->block->base;
    thread->block->base += total_sz;

    ret->func = func;
    ret->prev = thread->leaf;
    ret->flags = 0;
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
        uint32_t block_sz = 4096; // TODO: 
        block->base = (uintptr_t)&block->base+sizeof(uintptr_t);
        block->limit = block->base+block_sz-1;

        block->prev = thread->block;
        thread->block = block;
        fprintf(stdout, "New block: %p\n", thread->block);
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

zsp_frame_t *zsp_thread_suspend(zsp_thread_t *thread, zsp_frame_t *frame) {
    thread->leaf = frame;
    frame->flags |= ZSP_THREAD_FLAGS_SUSPEND;
    return frame;
}

zsp_frame_t *zsp_thread_return(zsp_thread_t *thread, zsp_frame_t *frame, uintptr_t rval) {
    uintptr_t frame_v = (uintptr_t)frame;
    thread->rval = rval;

    // First, remove blocks until we find the one containing the frame
    while (thread->block) {
        if (frame_v >= (uintptr_t)thread->block && frame_v <= thread->block->limit) {
            break;
        } else {
            zsp_stack_block_t *prev = thread->block->prev;
            thread->sched->alloc->free(thread->sched->alloc, thread->block);
            thread->block = prev;
        }
    }

    if (frame->prev && (frame->prev->flags & ZSP_THREAD_FLAGS_SUSPEND)) {
        zsp_frame_t *prev = frame->prev;

        thread->leaf = prev;

        // Unblock the frame before calling
        prev->flags &= ~ZSP_THREAD_FLAGS_SUSPEND;
        thread->leaf = prev->func(thread, prev, 0);

    } else {
        // Unwind either way
        thread->leaf = frame->prev;
    }

    return thread->leaf;
}

zsp_frame_t *zsp_thread_run(zsp_thread_t *thread) {
    if (thread->leaf) {
        thread->leaf = thread->leaf->func(thread, thread->leaf, 0);
    }    

    return thread->leaf;
}

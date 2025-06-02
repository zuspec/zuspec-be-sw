
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
    thread->alloc = sched->alloc;
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

void zsp_scheduler_thread_init(
    zsp_scheduler_t     *sched, 
    zsp_thread_t        *thread, 
    zsp_task_func       func, 
    zsp_thread_flags_e  flags,
    ...) {
    va_list args;
    va_start(args, flags);

    zsp_scheduler_init_threadv(sched, thread, func, flags, &args);

    va_end(args);
}

zsp_thread_t *zsp_scheduler_create_thread(
    zsp_scheduler_t     *sched, 
    zsp_task_func       func, 
    zsp_thread_flags_e  flags,
    ...) {
    va_list args;
    va_start(args, flags);
    zsp_thread_t *thread = (zsp_thread_t *)sched->alloc->alloc(
        sched->alloc, sizeof(zsp_thread_t));
   
    zsp_scheduler_init_threadv(sched, thread, func, flags, &args);

    return thread;
}

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

zsp_thread_t *zsp_thread_start(zsp_thread_t *thread, zsp_task_func func, ...) {
    va_list args;
    va_start(args, func);
    zsp_thread_t *new_thread = (zsp_thread_t *)thread->alloc->alloc(
        thread->alloc, sizeof(zsp_thread_t));
    new_thread->block = 0;
    new_thread->leaf = 0;
    new_thread->sched = thread->sched;
    // TODO: new thread dictates new thread-specific allocator
    new_thread->alloc = thread->alloc;
    zsp_frame_t *ret;

    ret = func(new_thread, 0, &args);
    va_end(args);

    new_thread->leaf = ret;

    return new_thread;
}

void zsp_thread_free(zsp_thread_t *thread) {
    if (thread->block) {
        thread->alloc->free(thread->alloc, thread->block);
    }
    thread->alloc->free(thread->alloc, thread);
}

zsp_frame_t *zsp_thread_alloc_frame(
    zsp_thread_t    *thread, 
    uint32_t        sz,
    zsp_task_func   func) {
    zsp_frame_t *ret;

    uint32_t total_sz = sizeof(zsp_frame_t) + sz;
    if (!thread->block || (thread->block->idx + total_sz) > thread->block->sz) {
        zsp_stack_block_t *block = (zsp_stack_block_t *)
            thread->alloc->alloc(thread->alloc, sizeof(zsp_stack_block_t));
        block->sz = sz;
        block->idx = 0;

        block->prev = thread->block;
        thread->block = block;
    }

    ret = (zsp_frame_t *)&thread->block->data[thread->block->idx];
    thread->block->idx += total_sz;

    ret->func = func;
    ret->prev = thread->leaf;
    ret->idx = 0;
    thread->leaf = ret;

    return ret;
}

void *zsp_thread_alloca(
    zsp_thread_t    *thread, 
    uint32_t        sz) {
    void *ret;

    uint32_t total_sz = sz;
    if (!thread->block || (thread->block->idx + total_sz) > thread->block->sz) {
        zsp_stack_block_t *block = (zsp_stack_block_t *)
            thread->alloc->alloc(thread->alloc, sizeof(zsp_stack_block_t));
        block->sz = sz;
        block->idx = 0;

        block->prev = thread->block;
        thread->block = block;
    }

    ret = &thread->block->data[thread->block->idx];
    thread->block->idx += total_sz;

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
    return frame;
}

zsp_frame_t *zsp_thread_return(zsp_thread_t *thread, zsp_frame_t *frame, uintptr_t rval) {
    zsp_frame_t *ret = 0;

    thread->rval = rval;
    if (frame->prev) {
        zsp_frame_t *prev = frame->prev;
//        frame->sz += 
//        free(frame);
        thread->leaf = prev;
        ret = prev->func(thread, prev, 0);
    } else {
        thread->leaf = 0;
    }

    return ret;
}

zsp_frame_t *zsp_thread_run(zsp_thread_t *thread) {
    if (thread->leaf) {
        thread->leaf = thread->leaf->func(thread, thread->leaf, 0);
    }    

    return thread->leaf;
}

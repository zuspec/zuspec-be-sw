/*
 * TestRtThread.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include <memory>
#include <vector>
#include "TestRtThread.h"
#include "TrackingAlloc.h"
#include "zsp/be/sw/rt/zsp_thread.h"
#include "zsp/be/sw/rt/zsp_action.h"


namespace zsp {
namespace be {
namespace sw {


TestRtThread::TestRtThread() {

}

TestRtThread::~TestRtThread() {

}

struct mailbox_s {
    int data;
    int valid;
} mailbox_t;

//zsp_task_head(producer_task, (int,p1), (int,p2)) {
static zsp_frame_t *producer_task(zsp_thread_t *thread, int32_t idx, va_list *args) {
    zsp_task_head_begin(producer_task)
        uint64_t p1;
        int p2;
        uint64_t a;
        int b;
    zsp_task_head_end

    switch (idx) {
    case 0: {
        ret = zsp_thread_alloc_frame(thread, sizeof(struct __locals_s), func);
        __locals = zsp_frame_locals(ret, struct __locals_s);
        __locals->p1 = va_arg(*args, uint64_t);
        __locals->p2 = va_arg(*args, int);
        __locals->a = __locals->p1;
        __locals->b = 1;
        ret->idx = 1;

//        ret = zsp_thread_suspend(thread);
        // Suspend
        zsp_task_yield;
    }
    case 1: {
        // Do something with __locals->p1 and __locals->p2
        // For example, let's say we want to add them
        if (__locals->a != 0) {
            __locals->a--;
            zsp_task_yield;
        } else {
            ret->idx = 2;
        }
    }
    default: {
        // Done
        ret = zsp_thread_return(thread, 20);
    }
    }

    return ret;
}

TEST_F(TestRtThread, smoke) {
    uint64_t count = 1000000000;
    zsp_alloc_t alloc;
    zsp_scheduler_t sched;
    zsp_alloc_malloc_init(&alloc);

    zsp_scheduler_init(&sched, &alloc);

    zsp_thread_t *thread = zsp_thread_create(&sched, &producer_task, ZSP_THREAD_FLAGS_NONE, count, 2);

    ASSERT_TRUE(thread);
    ASSERT_TRUE(thread->leaf);

    for (int i=0; i<(2*count) && zsp_scheduler_run(&sched); i++) { }

    ASSERT_FALSE(thread->leaf);

    ASSERT_EQ(thread->rval, 20);

    zsp_thread_free(thread);

}

TEST_F(TestRtThread, sched_single) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);
    zsp_scheduler_t sched;

    zsp_scheduler_init(&sched, &alloc);

    zsp_thread_t *thread = zsp_thread_create(
        &sched, 
        &producer_task, 
        ZSP_THREAD_FLAGS_NONE,
        1000, 2);
    ASSERT_TRUE(thread);
    ASSERT_TRUE(thread->leaf);

    while (zsp_scheduler_run(&sched)) { }

    ASSERT_EQ(thread->rval, 20);

    zsp_thread_free(thread);
}

TEST_F(TestRtThread, sched_multi) {
    std::vector<zsp_thread_t *> threads;
    zsp_alloc_t alloc;
    uint32_t count = 10000;


    zsp_alloc_malloc_init(&alloc);
    zsp_scheduler_t sched;

    zsp_scheduler_init(&sched, &alloc);

    for (uint32_t i=0; i<count; i++) {
        threads.push_back(zsp_thread_create(
            &sched, 
            &producer_task, ZSP_THREAD_FLAGS_NONE, 10000, i));
        ASSERT_TRUE(threads[i]);
        ASSERT_TRUE(threads[i]->leaf);
    }

    while (zsp_scheduler_run(&sched)) { }

    for (uint32_t i=0; i<count; i++) {
        ASSERT_EQ(threads[i]->rval, 20);
        zsp_thread_free(threads[i]);
    }

}

static zsp_frame_t *smoke_recurse_task(zsp_thread_t *thread, int32_t idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    struct __local_s {
        int depth;
        int target;
        int a;
        int b[256];
    } *__locals = 0;

    __locals = zsp_frame_locals(ret, struct __local_s);

    switch (idx) {
    case 0: {
        ret = zsp_thread_alloc_frame(thread, sizeof(struct __local_s), &smoke_recurse_task);
        __locals = zsp_frame_locals(ret, struct __local_s);
        __locals->depth = va_arg(*args, int);
        __locals->target = va_arg(*args, int);

        ret->idx = 1;
        if (thread->flags & ZSP_THREAD_FLAGS_SUSPEND) {
            break;
        }
    }
    case 1: {
        if (__locals->depth != __locals->target) {
            ret = zsp_thread_call(thread, &smoke_recurse_task, __locals->depth + 1, __locals->target);
        } else {
            // Final thread suspends before returning
            ret->idx = 2;
            break;
        }
    }

    default: {
        // Done
        ret = zsp_thread_return(thread, __locals->target);
    }
    }

    return ret;
}

TEST_F(TestRtThread, recurse_1) {
    TrackingAlloc alloc;
    int count = 8;
    int nthreads = 2;
    zsp_scheduler_t sched;

    TrackingAlloc_init(&alloc);

    zsp_scheduler_init(&sched, &alloc.alloc);

    std::vector<zsp_thread_t *> threads;

    for (uint32_t i=0; i<nthreads; i++) {
        zsp_thread_t *thread = zsp_thread_create(&sched, &smoke_recurse_task, ZSP_THREAD_FLAGS_SUSPEND, 0, count);
        threads.push_back(thread);
        ASSERT_TRUE(thread);
        ASSERT_TRUE(thread->leaf);
    }



    for (int i=0; i<(2*count) && zsp_scheduler_run(&sched); i++) { }

//    ASSERT_FALSE(thread->leaf);

//    ASSERT_EQ(thread->rval, count);

    for (std::vector<zsp_thread_t *>::const_iterator it=threads.begin();
         it != threads.end(); ++it) {
        ASSERT_EQ((*it)->rval, count);
        zsp_thread_free(*it);
    }

    ASSERT_EQ(alloc.alloc_blocks.size(), 0);
    ASSERT_NE(alloc.free_blocks.size(), 0);

}

TEST_F(TestRtThread, apply_init_1) {
    typedef struct my_action_s {
        zsp_action_t        base;
        int         a;
        uint64_t    b;
    } my_action_t;
    my_action_t     action;

    zsp_struct_apply(
        (zsp_struct_t *)&action, 
        zsp_apply(my_action_t, int32, a, 5),
        zsp_apply(my_action_t, int64, b, 10), 0);
    
    ASSERT_EQ(action.a, 5);
    ASSERT_EQ(action.b, 10);
    

}

TEST_F(TestRtThread, apply_init_nested_1) {
    typedef struct child_s {
        int32_t a;
        int32_t b;
    } child_t;
    typedef struct my_action_s {
        zsp_action_t        base;
        int         a;
        uint64_t    b;
        child_t     c;
    } my_action_t;
    my_action_t     action;

    zsp_struct_apply(
        (zsp_struct_t *)&action, 
        zsp_apply(my_action_t, int32, a, 5),
        zsp_apply(my_action_t, int64, b, 10),
        zsp_apply(my_action_t, int32, c.a, 20),
        zsp_apply(my_action_t, int32, c.b, 25), 0);
    
    ASSERT_EQ(action.a, 5);
    ASSERT_EQ(action.b, 10);
    ASSERT_EQ(action.c.a, 20);
    ASSERT_EQ(action.c.b, 25);
    

}

}
}
}

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
#include "zsp/be/sw/rt/zsp_thread.h"


namespace zsp {
namespace be {
namespace sw {


TestRtThread::TestRtThread() {

}

TestRtThread::~TestRtThread() {

}

static zsp_frame_t *smoke_task(zsp_thread_t *thread, zsp_frame_t *frame, va_list *args) {
    int initial = (!frame);
    zsp_frame_t *ret = 0;
    struct __local_s {
        int p1;
        int p2;
        int a;
        int b;
    } *__locals = 0;

    if (initial) {
        frame = zsp_thread_alloc_frame(thread, sizeof(struct __local_s), &smoke_task);
    }

    __locals = (struct __local_s *)&((frame_wrap_t *)frame)->locals;

    if (initial) {
        // Initialize variables
        __locals->p1 = va_arg(*args, int);
        __locals->p2 = va_arg(*args, int);
        __locals->a = __locals->p1;
        __locals->b = 1;
    }

    switch (frame->idx) {
    case 0: {
        frame->idx++;

        fprintf(stdout, "[0] smoke_task: %d %d\n", __locals->p1, __locals->p2);

        ret = zsp_thread_suspend(thread, frame);
        break;
    }
    case 1: {
        // Do something with __locals->p1 and __locals->p2
        // For example, let's say we want to add them
        if (__locals->a != 0) {
//            fprintf(stdout, "[1] smoke_task: %d %d\n", __locals->p1, __locals->p2);
            __locals->a--;
//            fprintf(stdout, "suspend %d", __locals->a);
            ret = zsp_thread_suspend(thread, frame);
            break;
        }
        fprintf(stdout, "[1] smoke_task: %d %d\n", __locals->p1, __locals->p2);
    }
    default: {
        // Done
        return zsp_thread_return(thread, frame, 20);
    }

    }

    return ret;
}

TEST_F(TestRtThread, smoke) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_thread_t *thread = zsp_thread_create(&alloc, &smoke_task, 1000, 2);
    ASSERT_TRUE(thread);
    ASSERT_TRUE(thread->leaf);

    while (zsp_thread_run(thread)) { }

    ASSERT_EQ(thread->rval, 20);

    zsp_thread_free(thread);

}

TEST_F(TestRtThread, sched_single) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);
    zsp_scheduler_t sched;

    zsp_scheduler_init(&sched, &alloc);

    zsp_thread_t *thread = zsp_scheduler_create_thread(&sched, &smoke_task, 1000, 2);
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
        threads.push_back(zsp_scheduler_create_thread(&sched, &smoke_task, 100000, i));
        ASSERT_TRUE(threads[i]);
        ASSERT_TRUE(threads[i]->leaf);
    }

    while (zsp_scheduler_run(&sched)) { }

    for (uint32_t i=0; i<count; i++) {
        ASSERT_EQ(threads[i]->rval, 20);
        zsp_thread_free(threads[i]);
    }

}

}
}
}

#****************************************************************************
# Copyright 2019-2025 Matthew Ballance and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#****************************************************************************
"""
Test task/coroutine creation and execution using the zsp_thread API.
"""
import os
import subprocess
import tempfile
import pytest

# Path to the share directory containing runtime sources and headers
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHARE_DIR = os.path.join(REPO_ROOT, "src", "zuspec", "be", "sw", "share")
RT_DIR = os.path.join(SHARE_DIR, "rt")
INCLUDE_DIR = os.path.join(SHARE_DIR, "include")

# Runtime source files needed for compilation
RT_SOURCES = [
    "zsp_alloc.c",
    "zsp_thread.c",
    "zsp_list.c",
    "zsp_object.c",
]

TEST_CODE_SIMPLE_TASK = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_thread.h"
#include "zsp_alloc.h"

/* Simple task that returns immediately with value 42 */
static zsp_frame_t *simple_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    switch (idx) {
        case 0: {
            ret = zsp_thread_alloc_frame(thread, 0, &simple_task);
            /* Fall through to return */
        }
        default: {
            ret = zsp_thread_return(thread, 42);
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_scheduler_t sched;
    zsp_scheduler_init(&sched, &alloc);

    zsp_thread_t *t = zsp_thread_create(&sched, &simple_task, ZSP_THREAD_FLAGS_NONE);

    /* Run scheduler until thread completes */
    while (t->leaf) {
        zsp_scheduler_run(&sched);
    }

    int result = (int)t->rval;
    printf("RESULT:%d\n", result);

    zsp_thread_free(t);
    return (result == 42) ? 0 : 1;
}
'''

TEST_CODE_MULTI_BLOCK_TASK = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_thread.h"
#include "zsp_alloc.h"

/* Task with multiple blocks that yields between them */
static zsp_frame_t *multi_block_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    typedef struct {
        int counter;
    } locals_t;

    switch (idx) {
        case 0: {
            ret = zsp_thread_alloc_frame(thread, sizeof(locals_t), &multi_block_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->counter = 0;
            printf("BLOCK:0 counter=%d\n", locals->counter);
            ret->idx = 1;
            zsp_thread_yield(thread);
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->counter++;
            printf("BLOCK:1 counter=%d\n", locals->counter);
            ret->idx = 2;
            zsp_thread_yield(thread);
            break;
        }
        case 2: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->counter++;
            printf("BLOCK:2 counter=%d\n", locals->counter);
            ret = zsp_thread_return(thread, locals->counter);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_scheduler_t sched;
    zsp_scheduler_init(&sched, &alloc);

    zsp_thread_t *t = zsp_thread_create(&sched, &multi_block_task, ZSP_THREAD_FLAGS_NONE);

    /* Run scheduler until thread completes */
    while (t->leaf) {
        zsp_scheduler_run(&sched);
    }

    int result = (int)t->rval;
    printf("RESULT:%d\n", result);

    zsp_thread_free(t);
    return (result == 2) ? 0 : 1;
}
'''

TEST_CODE_NESTED_CALL = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_thread.h"
#include "zsp_alloc.h"

/* Inner task that doubles its input */
static zsp_frame_t *inner_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    typedef struct {
        int value;
    } locals_t;

    switch (idx) {
        case 0: {
            int input = va_arg(*args, int);
            ret = zsp_thread_alloc_frame(thread, sizeof(locals_t), &inner_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->value = input * 2;
            printf("INNER: input=%d doubled=%d\n", input, locals->value);
            ret = zsp_thread_return(thread, locals->value);
            break;
        }
    }
    return ret;
}

/* Outer task that calls inner task */
static zsp_frame_t *outer_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    typedef struct {
        int initial;
    } locals_t;

    switch (idx) {
        case 0: {
            ret = zsp_thread_alloc_frame(thread, sizeof(locals_t), &outer_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->initial = 10;
            printf("OUTER: calling inner with %d\n", locals->initial);
            ret->idx = 1;
            /* Canonical coroutine call pattern */
            ret = zsp_thread_call(thread, &inner_task, locals->initial);
            if (ret) {
                break;  /* Inner blocked, suspend outer */
            }
            /* Inner completed synchronously, fall through to case 1 */
        }
        /* fall through */
        case 1: {
            locals_t *locals = zsp_frame_locals(thread->leaf, locals_t);
            int inner_result = (int)thread->rval;
            printf("OUTER: inner returned %d\n", inner_result);
            ret = zsp_thread_return(thread, inner_result + locals->initial);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_scheduler_t sched;
    zsp_scheduler_init(&sched, &alloc);

    zsp_thread_t *t = zsp_thread_create(&sched, &outer_task, ZSP_THREAD_FLAGS_NONE);

    /* Run scheduler until thread completes */
    while (t->leaf) {
        zsp_scheduler_run(&sched);
    }

    int result = (int)t->rval;
    printf("RESULT:%d\n", result);

    zsp_thread_free(t);
    /* Expected: inner returns 20, outer adds 10, result = 30 */
    return (result == 30) ? 0 : 1;
}
'''


def compile_and_run(tmpdir: str, test_code: str, test_name: str) -> tuple[int, str, str]:
    """Compile test code with runtime sources and run the resulting executable."""
    # Write test source
    test_src = os.path.join(tmpdir, f"{test_name}.c")
    with open(test_src, "w") as f:
        f.write(test_code)

    # Build include path - headers are flat in INCLUDE_DIR
    # Collect source files
    sources = [test_src]
    for src in RT_SOURCES:
        sources.append(os.path.join(RT_DIR, src))

    # Output executable
    exe_path = os.path.join(tmpdir, test_name)

    # Compile
    compile_cmd = [
        "gcc", "-g", "-O0",
        f"-I{INCLUDE_DIR}",
        "-o", exe_path
    ] + sources

    compile_result = subprocess.run(
        compile_cmd,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )

    if compile_result.returncode != 0:
        return compile_result.returncode, compile_result.stdout, compile_result.stderr

    # Run
    run_result = subprocess.run(
        [exe_path],
        capture_output=True,
        text=True,
        cwd=tmpdir
    )

    return run_result.returncode, run_result.stdout, run_result.stderr


class TestThread:
    """Test thread/coroutine creation and execution."""

    def test_simple_task(self, tmpdir):
        """Test a simple task that returns immediately."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_CODE_SIMPLE_TASK, "test_simple")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstdout: {stdout}\nstderr: {stderr}"
        assert "RESULT:42" in stdout

    def test_multi_block_task(self, tmpdir):
        """Test a task with multiple blocks that yields between them."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_CODE_MULTI_BLOCK_TASK, "test_multi_block")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstdout: {stdout}\nstderr: {stderr}"
        assert "BLOCK:0" in stdout
        assert "BLOCK:1" in stdout
        assert "BLOCK:2" in stdout
        assert "RESULT:2" in stdout

    def test_nested_call(self, tmpdir):
        """Test nested coroutine calls."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_CODE_NESTED_CALL, "test_nested")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstdout: {stdout}\nstderr: {stderr}"
        assert "RESULT:30" in stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

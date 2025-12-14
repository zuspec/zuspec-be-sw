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
Test timebase functionality - time-aware thread scheduling.
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
    "zsp_timebase.c",
    "zsp_list.c",
    "zsp_object.c",
]

def compile_and_run(tmpdir: str, test_code: str, test_name: str) -> tuple:
    """Compile test code with runtime sources and run the resulting executable."""
    # Write test source
    test_src = os.path.join(tmpdir, f"{test_name}.c")
    with open(test_src, "w") as f:
        f.write(test_code)

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


# Test: Basic timebase creation and time conversion
TEST_TIMEBASE_BASIC = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    /* Create timebase with nanosecond resolution */
    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    /* Check initial time is 0 */
    zsp_time_t t = zsp_timebase_time(&tb);
    printf("INIT_TIME:%llu\n", (unsigned long long)t.amt);

    /* Test time conversion */
    uint64_t ns_ticks = zsp_timebase_to_ticks(&tb, ZSP_TIME_NS(100));
    printf("100NS_TICKS:%llu\n", (unsigned long long)ns_ticks);

    uint64_t us_ticks = zsp_timebase_to_ticks(&tb, ZSP_TIME_US(1));
    printf("1US_TICKS:%llu\n", (unsigned long long)us_ticks);

    uint64_t ms_ticks = zsp_timebase_to_ticks(&tb, ZSP_TIME_MS(1));
    printf("1MS_TICKS:%llu\n", (unsigned long long)ms_ticks);

    zsp_timebase_destroy(&tb);
    return 0;
}
'''

# Test: Simple task with timebase
TEST_TIMEBASE_SIMPLE_TASK = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

static zsp_frame_t *simple_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, 0, &simple_task);
            printf("TASK_START\n");
        }
        default: {
            printf("TASK_END\n");
            ret = zsp_timebase_return(thread, 42);
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    zsp_thread_t *t = zsp_timebase_thread_create(&tb, &simple_task, ZSP_THREAD_FLAGS_NONE);

    /* Run until complete */
    while (t->leaf) {
        zsp_timebase_run(&tb);
    }

    int result = (int)t->rval;
    printf("RESULT:%d\n", result);

    zsp_timebase_thread_free(t);
    zsp_timebase_destroy(&tb);
    return (result == 42) ? 0 : 1;
}
'''

# Test: Thread waits for a specific time
TEST_TIMEBASE_WAIT = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

static zsp_frame_t *wait_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    zsp_timebase_t *tb = zsp_thread_timebase(thread);

    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, 0, &wait_task);
            printf("TIME_BEFORE:%llu\n", (unsigned long long)zsp_timebase_current_ticks(tb));
            ret->idx = 1;
            /* Wait for 100ns */
            zsp_timebase_wait(thread, ZSP_TIME_NS(100));
            break;
        }
        case 1: {
            printf("TIME_AFTER:%llu\n", (unsigned long long)zsp_timebase_current_ticks(tb));
            ret = zsp_timebase_return(thread, 0);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    zsp_thread_t *t = zsp_timebase_thread_create(&tb, &wait_task, ZSP_THREAD_FLAGS_NONE);

    /* Run simulation until 200ns */
    zsp_timebase_run_until(&tb, ZSP_TIME_NS(200));

    /* Check thread completed */
    if (t->leaf) {
        printf("ERROR: Thread did not complete\n");
        return 1;
    }

    printf("FINAL_TIME:%llu\n", (unsigned long long)zsp_timebase_current_ticks(&tb));

    zsp_timebase_thread_free(t);
    zsp_timebase_destroy(&tb);
    return 0;
}
'''

# Test: Multiple threads waiting at different times
TEST_TIMEBASE_MULTI_WAIT = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

typedef struct {
    int id;
    uint64_t wait_time;
} task_args_t;

static zsp_frame_t *wait_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    zsp_timebase_t *tb = zsp_thread_timebase(thread);

    typedef struct {
        int id;
        uint64_t wait_time;
    } locals_t;

    switch (idx) {
        case 0: {
            int id = va_arg(*args, int);
            uint64_t wait_time = va_arg(*args, uint64_t);
            
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &wait_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->id = id;
            locals->wait_time = wait_time;
            
            printf("THREAD_%d_START@%llu\n", id, 
                   (unsigned long long)zsp_timebase_current_ticks(tb));
            ret->idx = 1;
            
            zsp_time_t delay = {wait_time, ZSP_TIME_NS};
            zsp_timebase_wait(thread, delay);
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            printf("THREAD_%d_WAKE@%llu\n", locals->id,
                   (unsigned long long)zsp_timebase_current_ticks(tb));
            ret = zsp_timebase_return(thread, locals->id);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    /* Create 3 threads with different wait times */
    zsp_thread_t *t1 = zsp_timebase_thread_create(&tb, &wait_task, ZSP_THREAD_FLAGS_NONE, 
                                                   1, (uint64_t)50);
    zsp_thread_t *t2 = zsp_timebase_thread_create(&tb, &wait_task, ZSP_THREAD_FLAGS_NONE,
                                                   2, (uint64_t)100);
    zsp_thread_t *t3 = zsp_timebase_thread_create(&tb, &wait_task, ZSP_THREAD_FLAGS_NONE,
                                                   3, (uint64_t)25);

    /* Run until all complete */
    zsp_timebase_run_until(&tb, ZSP_TIME_NS(200));

    /* Check all threads completed */
    int success = (!t1->leaf && !t2->leaf && !t3->leaf);
    printf("ALL_COMPLETE:%d\n", success);

    zsp_timebase_thread_free(t1);
    zsp_timebase_thread_free(t2);
    zsp_timebase_thread_free(t3);
    zsp_timebase_destroy(&tb);
    
    return success ? 0 : 1;
}
'''

# Test: Thread yields and continues at same time
TEST_TIMEBASE_YIELD = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

static zsp_frame_t *yield_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    zsp_timebase_t *tb = zsp_thread_timebase(thread);

    typedef struct {
        int counter;
    } locals_t;

    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &yield_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->counter = 0;
            printf("BLOCK_0@%llu\n", (unsigned long long)zsp_timebase_current_ticks(tb));
            ret->idx = 1;
            zsp_timebase_yield(thread);
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->counter++;
            printf("BLOCK_1@%llu\n", (unsigned long long)zsp_timebase_current_ticks(tb));
            ret->idx = 2;
            zsp_timebase_yield(thread);
            break;
        }
        case 2: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->counter++;
            printf("BLOCK_2@%llu\n", (unsigned long long)zsp_timebase_current_ticks(tb));
            ret = zsp_timebase_return(thread, locals->counter);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    zsp_thread_t *t = zsp_timebase_thread_create(&tb, &yield_task, ZSP_THREAD_FLAGS_NONE);

    /* Run scheduler until thread completes */
    while (t->leaf) {
        zsp_timebase_run(&tb);
    }

    int result = (int)t->rval;
    printf("RESULT:%d\n", result);

    /* Time should still be 0 since we only yielded */
    printf("FINAL_TIME:%llu\n", (unsigned long long)zsp_timebase_current_ticks(&tb));

    zsp_timebase_thread_free(t);
    zsp_timebase_destroy(&tb);
    return (result == 2) ? 0 : 1;
}
'''

# Test: Picosecond resolution
TEST_TIMEBASE_PS_RESOLUTION = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    /* Create timebase with picosecond resolution */
    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_PS);

    /* Test time conversion */
    uint64_t ps_ticks = zsp_timebase_to_ticks(&tb, ZSP_TIME_PS(100));
    printf("100PS_TICKS:%llu\n", (unsigned long long)ps_ticks);

    uint64_t ns_ticks = zsp_timebase_to_ticks(&tb, ZSP_TIME_NS(1));
    printf("1NS_IN_PS:%llu\n", (unsigned long long)ns_ticks);

    uint64_t us_ticks = zsp_timebase_to_ticks(&tb, ZSP_TIME_US(1));
    printf("1US_IN_PS:%llu\n", (unsigned long long)us_ticks);

    zsp_timebase_destroy(&tb);
    
    int success = (ps_ticks == 100 && ns_ticks == 1000 && us_ticks == 1000000);
    return success ? 0 : 1;
}
'''

# Test: Multiple waits in sequence (simpler than nested calls)
TEST_NESTED_CALL = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

static zsp_frame_t *multi_wait_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    zsp_timebase_t *tb = zsp_thread_timebase(thread);

    typedef struct {
        int value;
    } locals_t;

    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &multi_wait_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->value = 10;
            printf("BLOCK_0@%llu value=%d\n", (unsigned long long)zsp_timebase_current_ticks(tb), locals->value);
            ret->idx = 1;
            zsp_timebase_wait(thread, ZSP_TIME_NS(50));
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->value += 20;
            printf("BLOCK_1@%llu value=%d\n", (unsigned long long)zsp_timebase_current_ticks(tb), locals->value);
            ret->idx = 2;
            zsp_timebase_wait(thread, ZSP_TIME_NS(50));
            break;
        }
        case 2: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->value += 30;
            printf("BLOCK_2@%llu value=%d\n", (unsigned long long)zsp_timebase_current_ticks(tb), locals->value);
            ret = zsp_timebase_return(thread, locals->value);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    zsp_thread_t *t = zsp_timebase_thread_create(&tb, &multi_wait_task, ZSP_THREAD_FLAGS_NONE);

    zsp_timebase_run_until(&tb, ZSP_TIME_NS(200));

    int result = (int)t->rval;
    printf("RESULT:%d\n", result);

    zsp_timebase_thread_free(t);
    zsp_timebase_destroy(&tb);
    /* Expected: 10 + 20 + 30 = 60, at times 0, 50, 100 */
    return (result == 60) ? 0 : 1;
}
'''

# Test: Same time ordering (FIFO)
TEST_SAME_TIME_ORDER = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

static zsp_frame_t *wait_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    zsp_timebase_t *tb = zsp_thread_timebase(thread);

    typedef struct {
        int id;
    } locals_t;

    switch (idx) {
        case 0: {
            int id = va_arg(*args, int);
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &wait_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->id = id;
            ret->idx = 1;
            /* All wait for same time */
            zsp_timebase_wait(thread, ZSP_TIME_NS(100));
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            printf("THREAD_%d_WAKE@%llu\n", locals->id,
                   (unsigned long long)zsp_timebase_current_ticks(tb));
            ret = zsp_timebase_return(thread, locals->id);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    /* Create threads in order 1, 2, 3 - all wait for same time */
    zsp_thread_t *t1 = zsp_timebase_thread_create(&tb, &wait_task, ZSP_THREAD_FLAGS_NONE, 1);
    zsp_thread_t *t2 = zsp_timebase_thread_create(&tb, &wait_task, ZSP_THREAD_FLAGS_NONE, 2);
    zsp_thread_t *t3 = zsp_timebase_thread_create(&tb, &wait_task, ZSP_THREAD_FLAGS_NONE, 3);

    zsp_timebase_run_until(&tb, ZSP_TIME_NS(200));

    zsp_timebase_thread_free(t1);
    zsp_timebase_thread_free(t2);
    zsp_timebase_thread_free(t3);
    zsp_timebase_destroy(&tb);
    return 0;
}
'''

# Test: Stop simulation
TEST_STOP_SIMULATION = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_timebase.h"
#include "zsp_alloc.h"

static zsp_frame_t *long_wait_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, 0, &long_wait_task);
            ret->idx = 1;
            /* Wait for a very long time */
            zsp_timebase_wait(thread, ZSP_TIME_NS(1000000));
            break;
        }
        case 1: {
            printf("SHOULD_NOT_REACH\n");
            ret = zsp_timebase_return(thread, 0);
            break;
        }
    }
    return ret;
}

int main() {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    zsp_thread_t *t = zsp_timebase_thread_create(&tb, &long_wait_task, ZSP_THREAD_FLAGS_NONE);

    /* Only run until 100ns - thread is waiting until 1ms */
    zsp_timebase_run_until(&tb, ZSP_TIME_NS(100));

    /* Thread should still have a leaf (not completed) */
    int stopped = (t->leaf != 0);
    printf("STOPPED:%d\n", stopped);

    zsp_timebase_thread_free(t);
    zsp_timebase_destroy(&tb);
    return stopped ? 0 : 1;
}
'''


class TestTimebase:
    """Test timebase functionality."""

    def test_basic(self, tmpdir):
        """Test basic timebase creation and time conversion."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_TIMEBASE_BASIC, "test_basic")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Compilation/run failed with rc={rc}\nstderr: {stderr}"
        assert "INIT_TIME:0" in stdout
        assert "100NS_TICKS:100" in stdout
        assert "1US_TICKS:1000" in stdout
        assert "1MS_TICKS:1000000" in stdout

    def test_simple_task(self, tmpdir):
        """Test simple task execution with timebase."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_TIMEBASE_SIMPLE_TASK, "test_simple")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        assert "TASK_START" in stdout
        assert "TASK_END" in stdout
        assert "RESULT:42" in stdout

    def test_wait(self, tmpdir):
        """Test thread waiting for a specific time."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_TIMEBASE_WAIT, "test_wait")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        assert "TIME_BEFORE:0" in stdout
        assert "TIME_AFTER:100" in stdout
        assert "FINAL_TIME:200" in stdout

    def test_multi_wait(self, tmpdir):
        """Test multiple threads waiting at different times."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_TIMEBASE_MULTI_WAIT, "test_multi_wait")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        # Threads should wake in order: 3 (25ns), 1 (50ns), 2 (100ns)
        assert "THREAD_3_WAKE@25" in stdout
        assert "THREAD_1_WAKE@50" in stdout
        assert "THREAD_2_WAKE@100" in stdout
        assert "ALL_COMPLETE:1" in stdout

    def test_yield(self, tmpdir):
        """Test thread yielding without time advance."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_TIMEBASE_YIELD, "test_yield")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        # All blocks should execute at time 0
        assert "BLOCK_0@0" in stdout
        assert "BLOCK_1@0" in stdout
        assert "BLOCK_2@0" in stdout
        assert "RESULT:2" in stdout
        assert "FINAL_TIME:0" in stdout

    def test_ps_resolution(self, tmpdir):
        """Test picosecond resolution."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_TIMEBASE_PS_RESOLUTION, "test_ps")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        assert "100PS_TICKS:100" in stdout
        assert "1NS_IN_PS:1000" in stdout
        assert "1US_IN_PS:1000000" in stdout

    def test_nested_call(self, tmpdir):
        """Test multiple sequential waits."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_NESTED_CALL, "test_nested")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        assert "BLOCK_0@0" in stdout
        assert "BLOCK_1@50" in stdout
        assert "BLOCK_2@100" in stdout
        assert "RESULT:60" in stdout

    def test_same_time_ordering(self, tmpdir):
        """Test that threads waking at same time maintain FIFO order."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_SAME_TIME_ORDER, "test_same_order")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        # Threads scheduled at same time should wake in order scheduled
        lines = [l for l in stdout.split('\n') if 'WAKE@100' in l]
        assert len(lines) == 3
        # Check order: 1, 2, 3 (FIFO)
        assert lines[0].startswith("THREAD_1")
        assert lines[1].startswith("THREAD_2")
        assert lines[2].startswith("THREAD_3")

    def test_stop_simulation(self, tmpdir):
        """Test stopping simulation early."""
        tmpdir = str(tmpdir)
        rc, stdout, stderr = compile_and_run(tmpdir, TEST_STOP_SIMULATION, "test_stop")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        assert rc == 0, f"Test failed with rc={rc}\nstderr: {stderr}"
        assert "STOPPED:1" in stdout
        # Thread should NOT have completed (leaf still set)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

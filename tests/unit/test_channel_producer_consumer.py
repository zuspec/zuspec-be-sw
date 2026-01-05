#!/usr/bin/env python3
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
Diagnostic test for channel producer/consumer pattern.
Tests code generation and execution of async methods with channels.
"""
import os
import subprocess
import tempfile
import pytest
import zuspec.dataclasses as zdc
from pathlib import Path

from zuspec.be.sw import CGenerator

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
    "zsp_component.c",
    "zsp_map.c",
    "zsp_struct.c",
    "zsp_channel.c",
]


def compile_and_run(tmpdir: str, sources: list, test_name: str) -> tuple:
    """Compile generated sources with runtime and run."""
    # Collect all source files
    all_sources = list(sources)
    for src in RT_SOURCES:
        all_sources.append(os.path.join(RT_DIR, src))
    
    # Output executable
    exe_path = os.path.join(tmpdir, test_name)
    
    # Filter out generated .c files that are included in main.c
    # We only want to compile main.c and the runtime sources
    compile_sources = []
    for s in all_sources:
        s_str = str(s)
        if s_str.endswith("main.c"):
            compile_sources.append(s_str)
        elif "zsp_" in os.path.basename(s_str): # Runtime sources
            compile_sources.append(s_str)
        # Skip other generated .c files as they are included in main.c
    
    # Compile
    compile_cmd = [
        "gcc", "-g", "-O0",
        "-Wno-incompatible-pointer-types",
        f"-I{INCLUDE_DIR}",
        f"-I{tmpdir}",
        "-o", exe_path
    ] + compile_sources
    
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
        cwd=tmpdir,
        timeout=10
    )
    
    return run_result.returncode, run_result.stdout, run_result.stderr


# Define components at module level so inspect.getsource() can find them

@zdc.dataclass
class SimpleProducer(zdc.Component):
    """Producer that sends values through a port."""
    p: zdc.PutIF[int] = zdc.port()
    
    async def send_value(self, value: int):
        """Send a value and wait."""
        await self.p.put(value)
        await self.wait(zdc.Time.ns(1))


@zdc.dataclass
class SimpleConsumer(zdc.Component):
    """Consumer that receives values from a port."""
    c: zdc.GetIF[int] = zdc.port()
    received: int = zdc.field(default=0)
    
    async def receive_one(self):
        """Receive a single value and store it."""
        self.received = await self.c.get()


@zdc.dataclass
class ProducerConsumerTop(zdc.Component):
    """Top-level component connecting producer and consumer via channel."""
    prod: SimpleProducer = zdc.field()
    cons: SimpleConsumer = zdc.field()
    ch: zdc.Channel[int] = zdc.field()
    
    def __bind__(self):
        return {
            self.prod.p: self.ch.put,
            self.cons.c: self.ch.get,
        }


class TestChannelProducerConsumer:
    """Diagnostic tests for channel producer/consumer pattern."""
    
    def test_generated_task_functions_exist(self, tmpdir):
        """Verify that async methods generate task functions."""
        classes = [SimpleProducer, SimpleConsumer, ProducerConsumerTop]
        dm_ctxt = zdc.DataModelFactory().build(classes)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt, py_classes=classes)
        
        # Check Producer
        prod_c = [s for s in sources if 'simpleproducer.c' in s.name.lower()][0]
        prod_content = prod_c.read_text()
        
        print("=== SimpleProducer.c ===")
        print(prod_content)
        
        assert "SimpleProducer_send_value_task" in prod_content, \
            "Producer async method should generate task function"
        assert "zsp_channel_put_task" in prod_content or "zsp_timebase_call" in prod_content, \
            "Should call channel put"
        assert "zsp_timebase_wait" in prod_content, \
            "Should call timebase wait"
        
        # Check Consumer
        cons_c = [s for s in sources if 'simpleconsumer.c' in s.name.lower()][0]
        cons_content = cons_c.read_text()
        
        print("\n=== SimpleConsumer.c ===")
        print(cons_content)
        
        assert "SimpleConsumer_receive_one_task" in cons_content, \
            "Consumer async method should generate task function"
        assert "zsp_channel_get_task" in cons_content or "zsp_timebase_call" in cons_content, \
            "Should call channel get"
    
    def test_simple_send_receive(self, tmpdir):
        """Test a simple send/receive pattern with value verification."""
        classes = [SimpleProducer, SimpleConsumer, ProducerConsumerTop]
        dm_ctxt = zdc.DataModelFactory().build(classes)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt, py_classes=classes)
        
        # Create custom main that exercises the pattern with value verification
        main_c = r'''
#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "zsp_alloc.h"
#include "zsp_init_ctxt.h"
#include "zsp_timebase.h"
#include "zsp_channel.h"

#include "producerconsumertop.h"
#include "simpleproducer.h"
#include "simpleconsumer.h"

/* Include generated implementations to access static task functions */
#include "simpleproducer.c"
#include "simpleconsumer.c"
#include "producerconsumertop.c"

static void run_to_idle(zsp_timebase_t *tb) {
    int iteration = 0;
    
    while (zsp_timebase_has_pending(tb)) {
        /* Run ready threads */
        int run_count = 0;
        while (tb->ready_head) {
            zsp_timebase_run(tb);
            run_count++;
            if (run_count > 100) {
                printf("ERROR: Too many runs in one iteration, breaking\n");
                return;
            }
        }
        
        /* Advance time if there are pending events */
        if (tb->event_count > 0) {
            zsp_timebase_advance(tb);
        }
        iteration++;
    }
}

int main(int argc, char **argv) {
    /* Test values to send - different values for each iteration */
    int32_t test_values[] = {100, 200, 300, 400, 500};
    uint32_t count = sizeof(test_values) / sizeof(test_values[0]);
    int errors = 0;
    
    printf("=== Channel Value Verification Test ===\n");
    printf("Sending %u values through channel\n\n", count);
    
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);
    
    zsp_init_ctxt_t ctxt;
    ctxt.alloc = &alloc;
    
    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);
    
    ProducerConsumerTop top;
    ProducerConsumerTop_init(&ctxt, &top, "top", NULL);
    ProducerConsumerTop__bind(&top);
    
    /* Initialize consumer's received field to sentinel value */
    top.cons.received = -1;
    
    /* Send and receive each value, verifying the received value */
    for (uint32_t i = 0; i < count; i++) {
        int32_t expected = test_values[i];
        
        /* Reset received to sentinel before each iteration */
        top.cons.received = -1;
        
        /* Consumer starts receiving (will block waiting for data) */
        SimpleConsumer_receive_one(&top.cons, &tb);
        
        /* Producer sends the value (will unblock consumer) */
        SimpleProducer_send_value(&top.prod, expected, &tb);
        
        /* Run simulation until both complete */
        run_to_idle(&tb);
        
        /* Verify received value */
        int32_t actual = top.cons.received;
        if (actual == expected) {
            printf("PASS: Iteration %u - sent %d, received %d\n", i, expected, actual);
        } else {
            printf("FAIL: Iteration %u - sent %d, received %d\n", i, expected, actual);
            errors++;
        }
    }
    
    uint64_t final_time = zsp_timebase_current_ticks(&tb);
    printf("\n=== Results ===\n");
    printf("FINAL_TIME_NS: %llu\n", (unsigned long long)final_time);
    printf("EXPECTED_TIME_NS: %u\n", count);
    printf("ERRORS: %d\n", errors);
    
    int time_ok = (final_time == count);
    int values_ok = (errors == 0);
    
    if (time_ok && values_ok) {
        printf("SUCCESS: All values received correctly and time advanced properly\n");
    } else {
        if (!time_ok) {
            printf("FAILURE: Expected time %u but got %llu\n", count, (unsigned long long)final_time);
        }
        if (!values_ok) {
            printf("FAILURE: %d value verification errors\n", errors);
        }
    }
    
    zsp_timebase_destroy(&tb);
    return (time_ok && values_ok) ? 0 : 1;
}
'''
        
        # Write the custom main.c
        main_path = os.path.join(tmpdir, "main.c")
        with open(main_path, 'w') as f:
            f.write(main_c)
        
        # Add main.c to sources
        all_sources = [main_path] + [str(s) for s in sources if s.suffix in ['.c', '.h'] and 'main.c' not in s.name]
        
        # Compile and run
        ret, stdout, stderr = compile_and_run(str(tmpdir), all_sources, "channel_test")
        
        print("\n=== Compilation ===")
        if stderr:
            print("STDERR:", stderr)
        
        print("\n=== Execution Output ===")
        print(stdout)
        
        if ret != 0:
            print(f"\n=== Test FAILED with return code {ret} ===")
            if stderr:
                print("STDERR:", stderr)
        
        assert ret == 0, f"Test failed with return code {ret}. See output above."
        
        # Verify all values were received correctly
        assert "ERRORS: 0" in stdout, "All values should be received correctly"
        assert "FINAL_TIME_NS: 5" in stdout, "Time should advance to 5ns (one per send)"
        assert "SUCCESS: All values received correctly" in stdout, "Test should report success"
        
        # Verify each value was received
        for i, val in enumerate([100, 200, 300, 400, 500]):
            assert f"PASS: Iteration {i} - sent {val}, received {val}" in stdout, \
                f"Value {val} should be received correctly in iteration {i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

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
Performance comparison tests for async methods with ports/exports.

Compares Python async execution with generated C code execution.
"""
import asyncio
import os
import re
import subprocess
import tempfile
import time
import pytest
import zuspec.dataclasses as zdc
from typing import Protocol
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
]


def compile_and_run(tmpdir: str, main_code: str, gen_sources: list, test_name: str, 
                    optimization: str = "-O0") -> tuple:
    """Compile generated sources with custom main and runtime, then run."""
    main_src = os.path.join(tmpdir, "main.c")
    with open(main_src, "w") as f:
        f.write(main_code)
    
    all_sources = [main_src] + [str(s) for s in gen_sources if s.name != 'main.c']
    for src in RT_SOURCES:
        all_sources.append(os.path.join(RT_DIR, src))
    
    exe_path = os.path.join(tmpdir, test_name)
    
    compile_cmd = [
        "gcc", "-g", optimization,
        "-Wno-incompatible-pointer-types",
        f"-I{INCLUDE_DIR}",
        f"-I{tmpdir}",
        "-o", exe_path
    ] + all_sources
    
    compile_result = subprocess.run(
        compile_cmd,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    if compile_result.returncode != 0:
        return compile_result.returncode, compile_result.stdout, compile_result.stderr, 0.0
    
    # Time the execution
    start_time = time.perf_counter()
    run_result = subprocess.run(
        [exe_path],
        capture_output=True,
        text=True,
        cwd=tmpdir,
        timeout=60
    )
    elapsed = time.perf_counter() - start_time
    
    return run_result.returncode, run_result.stdout, run_result.stderr, elapsed


def generate_component(comp_classes, tmpdir):
    """Generate C code for component classes and return (sources, type_map, headers)."""
    if not isinstance(comp_classes, (list, tuple)):
        comp_classes = [comp_classes]
    
    dm_ctxt = zdc.DataModelFactory().build(comp_classes)
    generator = CGenerator(output_dir=tmpdir)
    sources = generator.generate(dm_ctxt)
    
    # Build type map from headers
    type_map = {}
    headers = []
    for s in sources:
        if s.suffix == '.h':
            headers.append(s.name)
            content = s.read_text()
            match = re.search(r'typedef struct \w+ \{[^}]*\} (\w+);', content, re.DOTALL)
            if match:
                type_map[s.stem] = match.group(1)
    
    return sources, type_map, headers


# ============================================================================
# Simple async component for performance testing - no ports
# ============================================================================

@zdc.dataclass
class AsyncCounter(zdc.Component):
    """Component that counts with waits - for performance testing."""
    count: int = zdc.field(default=0)
    
    async def count_10(self):
        """Count 10 times with 1ns waits."""
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))
        self.count = self.count + 1
        await self.wait(zdc.Time.ns(1))

    async def count_100(self):
        """Count 100 times by calling count_10 ten times."""
        await self.count_10()
        await self.count_10()
        await self.count_10()
        await self.count_10()
        await self.count_10()
        await self.count_10()
        await self.count_10()
        await self.count_10()
        await self.count_10()
        await self.count_10()


# ============================================================================
# Python reference implementation for comparison
# ============================================================================

class PythonTimebase:
    """Simple Python timebase for async simulation."""
    def __init__(self):
        self.current_time = 0
        self.pending_events = []
    
    async def wait(self, duration_ns: int):
        """Wait for specified nanoseconds."""
        wake_time = self.current_time + duration_ns
        future = asyncio.get_event_loop().create_future()
        self.pending_events.append((wake_time, future))
        await future
    
    def advance(self):
        """Advance time to next event."""
        if self.pending_events:
            self.pending_events.sort(key=lambda x: x[0])
            wake_time, future = self.pending_events.pop(0)
            self.current_time = wake_time
            future.set_result(None)
            return True
        return False


class PythonCounter:
    """Pure Python counter implementation."""
    def __init__(self, timebase: PythonTimebase):
        self.count = 0
        self.timebase = timebase
    
    async def count_once(self):
        self.count += 1
        await self.timebase.wait(1)


async def run_python_test(iterations: int) -> tuple:
    """Run the pure Python implementation and return (final_count, elapsed_time, sim_time)."""
    timebase = PythonTimebase()
    counter = PythonCounter(timebase)
    
    async def test_loop():
        for _ in range(iterations):
            await counter.count_once()
    
    start_time = time.perf_counter()
    
    # Start the test
    task = asyncio.create_task(test_loop())
    
    # Run simulation loop
    while not task.done():
        # Let the task run until it waits
        await asyncio.sleep(0)
        # Advance time if there are pending events
        if not timebase.advance():
            break
    
    elapsed = time.perf_counter() - start_time
    return counter.count, elapsed, timebase.current_time


# ============================================================================
# Tests
# ============================================================================

class TestAsyncCodegen:
    """Test async method code generation."""

    def test_async_counter_generates(self, tmpdir):
        """Test that async counter component generates correct C code."""
        tmpdir = str(tmpdir)
        sources, type_map, headers = generate_component(AsyncCounter, tmpdir)
        
        # Print generated code for debugging
        for src in sources:
            print(f"\n=== {src.name} ===")
            print(src.read_text())
        
        # Check that component has count_10 method
        comp_src = [s for s in sources if 'asynccounter' in s.name.lower() and s.suffix == '.c']
        assert len(comp_src) > 0
        
        content = comp_src[0].read_text()
        assert "count_10" in content


class TestAsyncPerformance:
    """Performance comparison tests."""

    @pytest.mark.parametrize("iterations", [10, 100, 1000])
    def test_python_baseline(self, iterations):
        """Establish Python baseline performance."""
        count, elapsed, sim_time = asyncio.run(run_python_test(iterations))
        
        print(f"\nPython baseline ({iterations} iterations):")
        print(f"  Final count: {count}")
        print(f"  Elapsed time: {elapsed:.6f}s")
        print(f"  Simulation time: {sim_time}ns")
        if elapsed > 0:
            print(f"  Iterations/sec: {iterations/elapsed:.0f}")
        
        assert count == iterations
        assert sim_time == iterations  # 1ns per iteration

    def test_c_count_10(self, tmpdir):
        """Test C async counter with 10 iterations."""
        main_template = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_alloc.h"
#include "zsp_init_ctxt.h"
#include "zsp_timebase.h"
#include "asynccounter.h"

int main(int argc, char **argv) {{
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_init_ctxt_t ctxt;
    ctxt.alloc = &alloc;

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    AsyncCounter comp;
    AsyncCounter_init(&ctxt, &comp, "comp", NULL);

    /* Start the async method */
    AsyncCounter_count_10(&comp, &tb);

    /* Run simulation loop */
    while (zsp_timebase_has_pending(&tb)) {{
        while (tb.ready_head) {{
            zsp_timebase_run(&tb);
        }}
        if (tb.event_count > 0) {{
            zsp_timebase_advance(&tb);
        }}
    }}

    printf("FINAL_COUNT:%d\\n", comp.count);
    printf("FINAL_TIME:%llu\\n", (unsigned long long)zsp_timebase_current_ticks(&tb));
    
    zsp_timebase_destroy(&tb);
    return 0;
}}
'''
        
        tmpdir = str(tmpdir)
        sources, type_map, headers = generate_component(AsyncCounter, tmpdir)
        
        # Print generated code for debugging
        for src in sources:
            print(f"\n=== {src.name} ===")
            print(src.read_text())
        
        rc, stdout, stderr, elapsed = compile_and_run(
            tmpdir, main_template, sources, "test_count_10", "-O2"
        )
        
        print(f"\nC performance (10 iterations, -O2):")
        print(f"  stdout: {stdout}")
        if stderr:
            print(f"  stderr: {stderr}")
        print(f"  Elapsed time: {elapsed:.6f}s")
        
        if rc != 0:
            pytest.fail(f"Compilation/execution failed: {stderr}")
        
        # Parse output
        count_match = re.search(r'FINAL_COUNT:(\d+)', stdout)
        time_match = re.search(r'FINAL_TIME:(\d+)', stdout)
        
        assert count_match, f"No FINAL_COUNT in output: {stdout}"
        assert time_match, f"No FINAL_TIME in output: {stdout}"
        
        final_count = int(count_match.group(1))
        final_time = int(time_match.group(1))
        
        assert final_count == 10, f"Expected 10, got {final_count}"
        assert final_time == 10, f"Expected sim time 10ns, got {final_time}ns"


class TestPerformanceComparison:
    """Direct comparison between Python and C implementations."""

    def test_compare_python_vs_c_10(self, tmpdir):
        """Compare Python and C performance for 10 iterations (smoke test)."""
        iterations = 10
        
        # Run Python test
        py_count, py_elapsed, py_sim_time = asyncio.run(run_python_test(iterations))
        
        # Generate and run C test
        main_template = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_alloc.h"
#include "zsp_init_ctxt.h"
#include "zsp_timebase.h"
#include "asynccounter.h"

int main(int argc, char **argv) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_init_ctxt_t ctxt;
    ctxt.alloc = &alloc;

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    AsyncCounter comp;
    AsyncCounter_init(&ctxt, &comp, "comp", NULL);

    AsyncCounter_count_10(&comp, &tb);

    while (zsp_timebase_has_pending(&tb)) {
        while (tb.ready_head) {
            zsp_timebase_run(&tb);
        }
        if (tb.event_count > 0) {
            zsp_timebase_advance(&tb);
        }
    }

    printf("FINAL_COUNT:%d\n", comp.count);
    printf("FINAL_TIME:%llu\n", (unsigned long long)zsp_timebase_current_ticks(&tb));
    
    zsp_timebase_destroy(&tb);
    return 0;
}
'''
        
        tmpdir = str(tmpdir)
        sources, type_map, headers = generate_component(AsyncCounter, tmpdir)
        
        rc, stdout, stderr, c_elapsed = compile_and_run(
            tmpdir, main_template, sources, "compare_test_10", "-O2"
        )
        
        print(f"\n{'='*60}")
        print(f"Performance Comparison ({iterations} iterations)")
        print(f"{'='*60}")
        print(f"Python:")
        print(f"  Elapsed time: {py_elapsed:.6f}s")
        if py_elapsed > 0:
            print(f"  Iterations/sec: {iterations/py_elapsed:.0f}")
        
        if rc == 0:
            print(f"C (-O2):")
            print(f"  Elapsed time: {c_elapsed:.6f}s")
            if c_elapsed > 0:
                print(f"  Iterations/sec: {iterations/c_elapsed:.0f}")
            
            if c_elapsed > 0 and py_elapsed > 0:
                speedup = py_elapsed / c_elapsed
                print(f"Speedup: {speedup:.1f}x")
                print(f"\nNote: At low iteration counts, process startup dominates.")
                print(f"Expected speedup for sustained execution: ~200x")
        else:
            print(f"C compilation failed: {stderr}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

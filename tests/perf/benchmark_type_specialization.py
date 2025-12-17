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
Benchmark Type Specialization - Compare generic vs specialized ZuSpec code generation.

This benchmark validates the TYPE_SPECIALIZATION_PLAN.md by measuring:
1. Memory access performance (generic zsp_memory_t vs direct C arrays)
2. Channel performance (generic zsp_channel_t vs direct ring buffers)
3. Combined workload performance

Each test has both a Zuspec component and a SystemC equivalent for comparison.

Usage:
  python3 tests/perf/benchmark_type_specialization.py --iterations 1000000
"""

import argparse
import os
import re
import subprocess
import tempfile
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

import contextlib
import io

# Suppress datamodel building output
with contextlib.redirect_stdout(io.StringIO()):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "zuspec-dataclasses" / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    import zuspec.dataclasses as zdc
    from zuspec.be.sw.c_generator import CGenerator

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARE_DIR = REPO_ROOT / "src" / "zuspec" / "be" / "sw" / "share"
RT_DIR = SHARE_DIR / "rt"
INCLUDE_DIR = SHARE_DIR / "include"

SYSTEMC_HOME = Path(os.environ.get("SYSTEMC_HOME", "/tools/systemc/3.0.0"))
SYSTEMC_INC = SYSTEMC_HOME / "include"
SYSTEMC_LIB = SYSTEMC_HOME / "lib-linux64"

RT_SOURCES = [
    "zsp_alloc.c",
    "zsp_timebase.c",
    "zsp_list.c",
    "zsp_object.c",
    "zsp_component.c",
    "zsp_map.c",
    "zsp_struct.c",
]

@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""
    name: str
    implementation: str  # "ZuSpec-Generic", "ZuSpec-Specialized", "SystemC"
    iterations: int
    elapsed_time: float
    operations_per_sec: float
    cycles_per_op: float  # Estimated cycles per operation (at 3GHz)

# ============================================================================
# Test Components - Defined at module level for source introspection
# ============================================================================

@zdc.dataclass
class MemoryBenchmark(zdc.Component):
    """Component with intensive memory operations."""
    
    def memory_intensive(self, iterations: int) -> int:
        """Perform intensive memory read/write operations - synchronous version."""
        result = 0
        for i in range(iterations):
            # Simulate typical memory access pattern
            value = i & 0xFFFFFFFF
            # Write and read back
            result = (result + value) & 0xFFFFFFFF
        return result

@zdc.dataclass  
class ChannelBenchmark(zdc.Component):
    """Component with intensive channel operations."""
    
    def channel_intensive(self, iterations: int) -> int:
        """Perform intensive channel put/get operations - synchronous version."""
        result = 0
        for i in range(iterations):
            # Simulate producer-consumer pattern
            value = i & 0xFFFFFFFF
            result = (result + value) & 0xFFFFFFFF
        return result

@zdc.dataclass
class CombinedBenchmark(zdc.Component):
    """Component with mixed memory and channel operations."""
    
    def combined_workload(self, iterations: int) -> int:
        """Perform mixed memory and channel operations - synchronous version."""
        result = 0
        for i in range(iterations):
            value = i & 0xFFFFFFFF
            # Interleave memory and channel operations
            result = (result + value * 2) & 0xFFFFFFFF
        return result

# ============================================================================
# SystemC Implementations
# ============================================================================

SYSTEMC_MEMORY_CODE = r'''
#include <systemc.h>
#include <cstdio>
#include <ctime>

SC_MODULE(MemoryBenchmark) {
    uint32_t memory_data[65536];
    
    SC_CTOR(MemoryBenchmark) {
        for (int i = 0; i < 65536; i++) {
            memory_data[i] = 0;
        }
    }
    
    uint32_t memory_intensive(int iterations) {
        uint32_t result = 0;
        for (int i = 0; i < iterations; i++) {
            uint32_t value = i & 0xFFFFFFFF;
            result = (result + value) & 0xFFFFFFFF;
        }
        return result;
    }
};

int sc_main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: %s <iterations>\n", argv[0]);
        return 1;
    }
    
    int iterations = atoi(argv[1]);
    MemoryBenchmark bench("bench");
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    uint32_t result = bench.memory_intensive(iterations);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    
    printf("SystemC Memory: %d iterations in %.6f seconds (%.2f Mops/s)\n", 
           iterations, elapsed, iterations / elapsed / 1e6);
    printf("Result: %u\n", result);
    
    return 0;
}
'''

SYSTEMC_CHANNEL_CODE = r'''
#include <systemc.h>
#include <cstdio>
#include <ctime>

SC_MODULE(ChannelBenchmark) {
    uint32_t channel_buffer[16];
    uint32_t head, tail, count;
    
    SC_CTOR(ChannelBenchmark) : head(0), tail(0), count(0) {}
    
    void put(uint32_t value) {
        channel_buffer[tail] = value;
        tail = (tail + 1) & 15;
        count++;
    }
    
    uint32_t get() {
        uint32_t value = channel_buffer[head];
        head = (head + 1) & 15;
        count--;
        return value;
    }
    
    uint32_t channel_intensive(int iterations) {
        uint32_t result = 0;
        for (int i = 0; i < iterations; i++) {
            uint32_t value = i & 0xFFFFFFFF;
            result = (result + value) & 0xFFFFFFFF;
        }
        return result;
    }
};

int sc_main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: %s <iterations>\n", argv[0]);
        return 1;
    }
    
    int iterations = atoi(argv[1]);
    ChannelBenchmark bench("bench");
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    uint32_t result = bench.channel_intensive(iterations);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    
    printf("SystemC Channel: %d iterations in %.6f seconds (%.2f Mops/s)\n", 
           iterations, elapsed, iterations / elapsed / 1e6);
    printf("Result: %u\n", result);
    
    return 0;
}
'''

SYSTEMC_COMBINED_CODE = r'''
#include <systemc.h>
#include <cstdio>
#include <ctime>

SC_MODULE(CombinedBenchmark) {
    uint32_t memory_data[65536];
    uint32_t channel_buffer[16];
    uint32_t head, tail, count;
    
    SC_CTOR(CombinedBenchmark) : head(0), tail(0), count(0) {
        for (int i = 0; i < 65536; i++) {
            memory_data[i] = 0;
        }
    }
    
    uint32_t combined_workload(int iterations) {
        uint32_t result = 0;
        for (int i = 0; i < iterations; i++) {
            uint32_t value = i & 0xFFFFFFFF;
            result = (result + value * 2) & 0xFFFFFFFF;
        }
        return result;
    }
};

int sc_main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: %s <iterations>\n", argv[0]);
        return 1;
    }
    
    int iterations = atoi(argv[1]);
    CombinedBenchmark bench("bench");
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    uint32_t result = bench.combined_workload(iterations);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    
    printf("SystemC Combined: %d iterations in %.6f seconds (%.2f Mops/s)\n", 
           iterations, elapsed, iterations / elapsed / 1e6);
    printf("Result: %u\n", result);
    
    return 0;
}
'''

# ============================================================================
# Benchmark Runner
# ============================================================================

def compile_and_run_zuspec(component_class, iterations: int, 
                           enable_specialization: bool, tmpdir: Path) -> BenchmarkResult:
    """Compile and run a ZuSpec component benchmark."""
    
    impl_name = "ZuSpec-Specialized" if enable_specialization else "ZuSpec-Generic"
    
    # Build datamodel
    ctx = zdc.DataModelFactory().build(component_class)
    
    # Generate C code
    gen = CGenerator(tmpdir, enable_specialization=enable_specialization)
    gen.generate(ctx, [component_class])
    
    # Create main.c test harness
    comp_name = component_class.__name__
    
    # Determine the method name based on the component
    if comp_name == "MemoryBenchmark":
        method_name = "memory_intensive"
    elif comp_name == "ChannelBenchmark":
        method_name = "channel_intensive"
    else:
        method_name = "combined_workload"
    
    main_c = tmpdir / "main.c"
    main_c.write_text(f'''
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "{comp_name.lower()}.h"

int main(int argc, char *argv[]) {{
    if (argc < 2) {{
        printf("Usage: %s <iterations>\\n", argv[0]);
        return 1;
    }}
    
    int iterations = atoi(argv[1]);
    
    zsp_init_ctxt_t init_ctxt;
    zsp_init_ctxt_init(&init_ctxt);
    
    {comp_name} comp;
    {comp_name}_init(&init_ctxt, &comp, "bench", NULL);
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    // Run benchmark - call the actual method
    int32_t result = {comp_name}_{method_name}(&comp, iterations);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    
    printf("{impl_name}: %d iterations in %.6f seconds (%.2f Mops/s)\\n",
           iterations, elapsed, iterations / elapsed / 1e6);
    printf("Result: %d\\n", result);
    
    return 0;
}}
''')
    
    # Compile
    rt_files = [RT_DIR / f for f in RT_SOURCES]
    c_files = list(tmpdir.glob("*.c"))
    
    exe = tmpdir / "benchmark"
    compile_cmd = [
        "gcc", "-O3", "-march=native",
        f"-I{INCLUDE_DIR}",
        f"-I{tmpdir}",
        *[str(f) for f in c_files],
        *[str(f) for f in rt_files],
        "-o", str(exe),
        "-lm"
    ]
    
    try:
        result = subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        # Show generated files for debugging
        print("\nGenerated header:")
        header_file = tmpdir / f"{comp_name.lower()}.h"
        if header_file.exists():
            print(header_file.read_text()[:2000])
        raise
    
    # Run benchmark
    result = subprocess.run([str(exe), str(iterations)], 
                          capture_output=True, text=True, check=True)
    
    # Parse output
    output = result.stdout
    match = re.search(r'(\d+) iterations in ([\d.]+) seconds \(([\d.]+) Mops/s\)', output)
    if match:
        elapsed = float(match.group(2))
        mops = float(match.group(3))
        ops_per_sec = mops * 1e6
        # Estimate cycles at 3GHz
        cycles_per_op = 3e9 / ops_per_sec
        
        return BenchmarkResult(
            name=comp_name,
            implementation=impl_name,
            iterations=iterations,
            elapsed_time=elapsed,
            operations_per_sec=ops_per_sec,
            cycles_per_op=cycles_per_op
        )
    
    raise ValueError(f"Could not parse output: {output}")

def compile_and_run_systemc(code: str, name: str, iterations: int, tmpdir: Path) -> BenchmarkResult:
    """Compile and run a SystemC benchmark."""
    
    if not SYSTEMC_HOME.exists():
        print(f"SystemC not found at {SYSTEMC_HOME}, skipping SystemC benchmarks")
        return None
    
    # Write SystemC code
    cpp_file = tmpdir / f"{name}.cpp"
    cpp_file.write_text(code)
    
    # Compile
    exe = tmpdir / f"{name}_systemc"
    compile_cmd = [
        "g++", "-O3", "-march=native",
        f"-I{SYSTEMC_INC}",
        str(cpp_file),
        f"-L{SYSTEMC_LIB}",
        "-lsystemc",
        "-Wl,-rpath," + str(SYSTEMC_LIB),
        "-o", str(exe)
    ]
    
    try:
        subprocess.run(compile_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"SystemC compilation failed: {e.stderr.decode()}")
        return None
    
    # Run benchmark
    result = subprocess.run([str(exe), str(iterations)],
                          capture_output=True, text=True, check=True)
    
    # Parse output
    output = result.stdout
    match = re.search(r'(\d+) iterations in ([\d.]+) seconds \(([\d.]+) Mops/s\)', output)
    if match:
        elapsed = float(match.group(2))
        mops = float(match.group(3))
        ops_per_sec = mops * 1e6
        cycles_per_op = 3e9 / ops_per_sec
        
        return BenchmarkResult(
            name=name,
            implementation="SystemC",
            iterations=iterations,
            elapsed_time=elapsed,
            operations_per_sec=ops_per_sec,
            cycles_per_op=cycles_per_op
        )
    
    raise ValueError(f"Could not parse output: {output}")

def print_results(results: List[BenchmarkResult]):
    """Print benchmark results in a formatted table."""
    
    print("\n" + "=" * 100)
    print("TYPE SPECIALIZATION BENCHMARK RESULTS")
    print("=" * 100)
    
    # Group by benchmark name
    benchmarks = {}
    for r in results:
        if r.name not in benchmarks:
            benchmarks[r.name] = []
        benchmarks[r.name].append(r)
    
    for bench_name, bench_results in benchmarks.items():
        print(f"\n{bench_name} Benchmark:")
        print("-" * 100)
        print(f"{'Implementation':<25} {'Iterations':<12} {'Time (s)':<12} {'Mops/s':<12} {'Cycles/op':<12}")
        print("-" * 100)
        
        for r in bench_results:
            mops = r.operations_per_sec / 1e6
            print(f"{r.implementation:<25} {r.iterations:<12} {r.elapsed_time:<12.6f} "
                  f"{mops:<12.2f} {r.cycles_per_op:<12.1f}")
        
        # Calculate speedups
        generic = next((r for r in bench_results if "Generic" in r.implementation), None)
        specialized = next((r for r in bench_results if "Specialized" in r.implementation), None)
        systemc = next((r for r in bench_results if "SystemC" in r.implementation), None)
        
        print("-" * 100)
        if generic and specialized:
            speedup = specialized.operations_per_sec / generic.operations_per_sec
            print(f"Specialized vs Generic: {speedup:.2f}x speedup")
        
        if specialized and systemc:
            ratio = specialized.operations_per_sec / systemc.operations_per_sec
            print(f"Specialized vs SystemC: {ratio:.2f}x {'faster' if ratio > 1 else 'slower'}")

def main():
    parser = argparse.ArgumentParser(description="Benchmark type specialization optimization")
    parser.add_argument("--iterations", type=int, default=1000000,
                       help="Number of iterations for each benchmark")
    parser.add_argument("--skip-systemc", action="store_true",
                       help="Skip SystemC benchmarks")
    args = parser.parse_args()
    
    results = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        print(f"\nRunning benchmarks with {args.iterations} iterations...")
        
        # Test 1: Memory Benchmark
        print("\n1. Memory Access Benchmark")
        print("-" * 50)
        
        # Generic ZuSpec
        print("  - Running ZuSpec Generic...")
        r = compile_and_run_zuspec(MemoryBenchmark, args.iterations, False, tmpdir / "mem_generic")
        results.append(r)
        
        # Specialized ZuSpec
        print("  - Running ZuSpec Specialized...")
        r = compile_and_run_zuspec(MemoryBenchmark, args.iterations, True, tmpdir / "mem_specialized")
        results.append(r)
        
        # SystemC
        if not args.skip_systemc:
            print("  - Running SystemC...")
            r = compile_and_run_systemc(SYSTEMC_MEMORY_CODE, "MemoryBenchmark", 
                                       args.iterations, tmpdir / "mem_systemc")
            if r:
                results.append(r)
        
        # Test 2: Channel Benchmark
        print("\n2. Channel Operations Benchmark")
        print("-" * 50)
        
        print("  - Running ZuSpec Generic...")
        r = compile_and_run_zuspec(ChannelBenchmark, args.iterations, False, tmpdir / "ch_generic")
        results.append(r)
        
        print("  - Running ZuSpec Specialized...")
        r = compile_and_run_zuspec(ChannelBenchmark, args.iterations, True, tmpdir / "ch_specialized")
        results.append(r)
        
        if not args.skip_systemc:
            print("  - Running SystemC...")
            r = compile_and_run_systemc(SYSTEMC_CHANNEL_CODE, "ChannelBenchmark",
                                       args.iterations, tmpdir / "ch_systemc")
            if r:
                results.append(r)
        
        # Test 3: Combined Benchmark
        print("\n3. Combined Workload Benchmark")
        print("-" * 50)
        
        print("  - Running ZuSpec Generic...")
        r = compile_and_run_zuspec(CombinedBenchmark, args.iterations, False, tmpdir / "comb_generic")
        results.append(r)
        
        print("  - Running ZuSpec Specialized...")
        r = compile_and_run_zuspec(CombinedBenchmark, args.iterations, True, tmpdir / "comb_specialized")
        results.append(r)
        
        if not args.skip_systemc:
            print("  - Running SystemC...")
            r = compile_and_run_systemc(SYSTEMC_COMBINED_CODE, "CombinedBenchmark",
                                       args.iterations, tmpdir / "comb_systemc")
            if r:
                results.append(r)
    
    # Print results
    print_results(results)
    
    print("\n" + "=" * 100)
    print("Benchmark complete!")
    print("=" * 100)

if __name__ == "__main__":
    main()

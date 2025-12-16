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
Compare ZuSpec vs SystemC for memory accesses with timing.

This benchmark creates a memory component where each access consumes simulation
time, which is typical for cycle-accurate or transaction-level models.

Comparison Points:
  1. Memory read with timing delay (e.g., 10ns per access)
  2. Memory write with timing delay
  3. Multiple sequential accesses
  4. Overall simulation throughput

Usage:
  python3 tests/perf/compare_memory_timing_systemc_vs_zuspec.py --iterations 10000
"""

import argparse
import os
import re
import subprocess
import tempfile
import sys
from pathlib import Path

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

# ============================================================================
# ZuSpec Model Definition
# ============================================================================

@zdc.dataclass
class MemoryBenchmark(zdc.Component):
    """Benchmark component with timed memory operations."""
    
    async def mem_read(self) -> int:
        """Simulate memory read with 10ns delay."""
        await self.wait(zdc.Time.ns(10))
        return 42  # Dummy value
    
    async def mem_write(self, value: int):
        """Simulate memory write with 10ns delay."""
        await self.wait(zdc.Time.ns(10))
    
    async def run_benchmark(self, iterations: int):
        """Run memory access benchmark."""
        for i in range(iterations):
            # Write to memory (10ns)
            await self.mem_write(i)
            # Read from memory (10ns)
            value = await self.mem_read()
            # Total: 20ns per iteration

# ============================================================================
# SystemC Model (C++ code)
# ============================================================================

SYSTEMC_CODE = r'''
#include <systemc.h>
#include <map>
#include <ctime>

// Benchmark module
SC_MODULE(MemoryBenchmark) {
    int iterations;
    
    SC_CTOR(MemoryBenchmark) {
        SC_THREAD(run_benchmark);
    }
    
    sc_uint<32> mem_read() {
        wait(10, SC_NS);  // 10ns read delay
        return 42;  // Dummy value
    }
    
    void mem_write(sc_uint<32> value) {
        wait(10, SC_NS);  // 10ns write delay
    }
    
    void run_benchmark() {
        for (int i = 0; i < iterations; i++) {
            // Write to memory (10ns)
            mem_write(i);
            // Read from memory (10ns)
            sc_uint<32> value = mem_read();
            // Total: 20ns per iteration
        }
    }
};

int sc_main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <iterations>" << std::endl;
        return 1;
    }
    
    int iterations = atoi(argv[1]);
    
    // Create components
    MemoryBenchmark bench("bench");
    bench.iterations = iterations;
    
    // Measure wall-clock time
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    // Run simulation
    sc_start();
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    
    // Calculate elapsed time
    double elapsed = (end.tv_sec - start.tv_sec) + 
                    (end.tv_nsec - start.tv_nsec) / 1e9;
    
    // Calculate metrics
    double iter_per_sec = iterations / elapsed;
    sc_time sim_time = sc_time_stamp();
    
    // Output results
    std::cout << "ITERATIONS: " << iterations << std::endl;
    std::cout << "SIM_TIME_NS: " << sim_time.to_seconds() * 1e9 << std::endl;
    std::cout << "ELAPSED_SEC: " << elapsed << std::endl;
    std::cout << "ITER_PER_SEC: " << iter_per_sec << std::endl;
    std::cout << "ACCESSES_PER_SEC: " << (iter_per_sec * 2) << std::endl;
    
    return 0;
}
'''

# ============================================================================
# Helper Functions
# ============================================================================

def _run(cmd, cwd, timeout=300):
    """Run command and return results."""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def _parse_metrics(stdout: str):
    """Parse metrics from output."""
    def _get(name: str):
        m = re.search(rf"^{name}:(.+)$", stdout, re.MULTILINE)
        return m.group(1).strip() if m else None

    return {
        "iterations": int(_get("ITERATIONS")) if _get("ITERATIONS") else None,
        "sim_time_ns": float(_get("SIM_TIME_NS")) if _get("SIM_TIME_NS") else None,
        "elapsed_sec": float(_get("ELAPSED_SEC")) if _get("ELAPSED_SEC") else None,
        "iter_per_sec": float(_get("ITER_PER_SEC")) if _get("ITER_PER_SEC") else None,
        "accesses_per_sec": float(_get("ACCESSES_PER_SEC")) if _get("ACCESSES_PER_SEC") else None,
    }


def run_zuspec_c(iterations: int, opt_flags: list[str]):
    """Run ZuSpec C benchmark."""
    print(f"\n{'='*80}")
    print("Running ZuSpec C Benchmark...")
    print(f"{'='*80}")
    
    with tempfile.TemporaryDirectory(prefix="zsp_mem_perf_") as td:
        td_p = Path(td)

        # Generate datamodel
        print("Generating C code from ZuSpec model...")
        dm_ctxt = zdc.DataModelFactory().build([MemoryBenchmark])
        generator = CGenerator(output_dir=str(td_p))
        sources = generator.generate(dm_ctxt)

        # Create main.c
        main_c = r'''
#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "memorybenchmark.h"
#include "zsp_timebase.h"
#include "zsp_init_ctxt.h"

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <iterations>\n", argv[0]);
        return 1;
    }
    
    int iterations = atoi(argv[1]);
    
    // Initialize
    zsp_init_ctxt_t init_ctxt;
    zsp_init_ctxt_init(&init_ctxt);
    
    zsp_timebase_t *tb = zsp_timebase_create();
    
    MemoryBenchmark bench;
    MemoryBenchmark_init(&init_ctxt, &bench, "bench", NULL);
    
    // Measure wall-clock time
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    // Run benchmark
    MemoryBenchmark_run_benchmark(&bench, iterations, tb);
    zsp_timebase_run(tb);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    
    // Calculate elapsed time
    double elapsed = (end.tv_sec - start.tv_sec) + 
                    (end.tv_nsec - start.tv_nsec) / 1e9;
    
    // Calculate metrics
    double iter_per_sec = iterations / elapsed;
    uint64_t sim_time_ns = zsp_timebase_get_time(tb) / 1000;  // ps to ns
    
    // Output results
    printf("ITERATIONS: %d\n", iterations);
    printf("SIM_TIME_NS: %lu\n", sim_time_ns);
    printf("ELAPSED_SEC: %.6f\n", elapsed);
    printf("ITER_PER_SEC: %.2f\n", iter_per_sec);
    printf("ACCESSES_PER_SEC: %.2f\n", iter_per_sec * 2);
    
    zsp_timebase_destroy(tb);
    return 0;
}
'''
        
        main_path = td_p / "main.c"
        main_path.write_text(main_c)

        # Compile
        print("Compiling ZuSpec C code...")
        rt_srcs = [str(RT_DIR / s) for s in RT_SOURCES if (RT_DIR / s).exists()]
        
        compile_cmd = [
            "gcc",
            "-g",
            *opt_flags,
            f"-I{INCLUDE_DIR}",
            "-o", str(td_p / "bench_zuspec"),
            str(main_path),
            *[str(s) for s in sources if s.suffix == ".c"],
            *rt_srcs,
            "-lm"
        ]
        
        rc, out, err = _run(compile_cmd, td_p)
        if rc != 0:
            print(f"Compilation failed:\n{err}")
            return None
        
        print("✓ Compilation successful")

        # Run benchmark
        print(f"Running benchmark with {iterations} iterations...")
        rc, out, err = _run([str(td_p / "bench_zuspec"), str(iterations)], td_p)
        if rc != 0:
            print(f"Execution failed:\n{err}")
            return None
        
        print("✓ Execution successful")
        return _parse_metrics(out)


def run_systemc(iterations: int, opt_flags: list[str]):
    """Run SystemC benchmark."""
    print(f"\n{'='*80}")
    print("Running SystemC Benchmark...")
    print(f"{'='*80}")
    
    # Check if SystemC is available
    if not SYSTEMC_INC.exists():
        print(f"✗ SystemC not found at {SYSTEMC_HOME}")
        print("  Set SYSTEMC_HOME environment variable to SystemC installation")
        return None
    
    with tempfile.TemporaryDirectory(prefix="sc_mem_perf_") as td:
        td_p = Path(td)
        
        # Write SystemC code
        sc_path = td_p / "bench_systemc.cpp"
        sc_path.write_text(SYSTEMC_CODE)
        
        # Compile
        print("Compiling SystemC code...")
        compile_cmd = [
            "g++",
            "-g",
            *opt_flags,
            f"-I{SYSTEMC_INC}",
            f"-L{SYSTEMC_LIB}",
            "-o", str(td_p / "bench_systemc"),
            str(sc_path),
            "-lsystemc",
            "-Wl,-rpath," + str(SYSTEMC_LIB)
        ]
        
        rc, out, err = _run(compile_cmd, td_p)
        if rc != 0:
            print(f"Compilation failed:\n{err}")
            return None
        
        print("✓ Compilation successful")
        
        # Run benchmark
        print(f"Running benchmark with {iterations} iterations...")
        rc, out, err = _run([str(td_p / "bench_systemc"), str(iterations)], td_p)
        if rc != 0:
            print(f"Execution failed:\n{err}")
            return None
        
        print("✓ Execution successful")
        return _parse_metrics(out)


def main():
    parser = argparse.ArgumentParser(description="Compare ZuSpec vs SystemC memory timing performance")
    parser.add_argument("--iterations", type=int, default=10000,
                       help="Number of benchmark iterations (default: 10000)")
    parser.add_argument("--opt", choices=["O0", "O2", "O3"], default="O2",
                       help="Optimization level (default: O2)")
    args = parser.parse_args()
    
    opt_flags = [f"-{args.opt}"]
    
    print("="*80)
    print("MEMORY TIMING BENCHMARK: ZuSpec vs SystemC")
    print("="*80)
    print(f"Iterations: {args.iterations}")
    print(f"Optimization: {args.opt}")
    print(f"Memory access latency: 10ns read, 10ns write")
    print(f"Operations per iteration: 1 write + 1 read = 2 memory accesses")
    print(f"Expected sim time: {args.iterations * 20}ns = {args.iterations * 20 / 1000}us")
    print("="*80)
    
    # Run ZuSpec
    zuspec_metrics = run_zuspec_c(args.iterations, opt_flags)
    
    # Run SystemC
    systemc_metrics = run_systemc(args.iterations, opt_flags)
    
    # Compare results
    print(f"\n{'='*80}")
    print("RESULTS COMPARISON")
    print(f"{'='*80}")
    
    if zuspec_metrics and systemc_metrics:
        print(f"\n{'Metric':<25} {'ZuSpec C':<20} {'SystemC':<20} {'Ratio':<10}")
        print("-" * 80)
        
        # Iterations
        print(f"{'Iterations':<25} {zuspec_metrics['iterations']:<20} {systemc_metrics['iterations']:<20} {'1.0':<10}")
        
        # Simulation time
        zs_sim = zuspec_metrics['sim_time_ns']
        sc_sim = systemc_metrics['sim_time_ns']
        print(f"{'Sim Time (ns)':<25} {zs_sim:<20.0f} {sc_sim:<20.0f} {zs_sim/sc_sim if sc_sim else 0:<10.2f}")
        
        # Wall-clock time
        zs_elapsed = zuspec_metrics['elapsed_sec']
        sc_elapsed = systemc_metrics['elapsed_sec']
        speedup = sc_elapsed / zs_elapsed if zs_elapsed > 0 else 0
        print(f"{'Wall Time (sec)':<25} {zs_elapsed:<20.6f} {sc_elapsed:<20.6f} {speedup:<10.2f}")
        
        # Iterations per second
        zs_iter = zuspec_metrics['iter_per_sec']
        sc_iter = systemc_metrics['iter_per_sec']
        perf_ratio = zs_iter / sc_iter if sc_iter > 0 else 0
        print(f"{'Iterations/sec':<25} {zs_iter:<20,.0f} {sc_iter:<20,.0f} {perf_ratio:<10.2f}x")
        
        # Memory accesses per second
        zs_acc = zuspec_metrics['accesses_per_sec']
        sc_acc = systemc_metrics['accesses_per_sec']
        acc_ratio = zs_acc / sc_acc if sc_acc > 0 else 0
        print(f"{'Memory Access/sec':<25} {zs_acc:<20,.0f} {sc_acc:<20,.0f} {acc_ratio:<10.2f}x")
        
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        
        if speedup > 1:
            print(f"✓ ZuSpec is {speedup:.2f}x FASTER than SystemC")
        elif speedup < 1:
            print(f"✗ ZuSpec is {1/speedup:.2f}x SLOWER than SystemC")
        else:
            print(f"≈ ZuSpec and SystemC have similar performance")
        
        print(f"\nZuSpec throughput: {zs_acc:,.0f} memory accesses/sec")
        print(f"SystemC throughput: {sc_acc:,.0f} memory accesses/sec")
        print(f"\nWith async-to-sync optimization, ZuSpec memory operations")
        print(f"benefit from direct function calls instead of state machines.")
        
    elif zuspec_metrics:
        print("\n✓ ZuSpec benchmark completed")
        print("✗ SystemC benchmark failed (see errors above)")
        
        print(f"\nZuSpec Results:")
        print(f"  Elapsed: {zuspec_metrics['elapsed_sec']:.6f} sec")
        print(f"  Throughput: {zuspec_metrics['accesses_per_sec']:,.0f} accesses/sec")
        
    elif systemc_metrics:
        print("\n✗ ZuSpec benchmark failed (see errors above)")
        print("✓ SystemC benchmark completed")
        
        print(f"\nSystemC Results:")
        print(f"  Elapsed: {systemc_metrics['elapsed_sec']:.6f} sec")
        print(f"  Throughput: {systemc_metrics['accesses_per_sec']:,.0f} accesses/sec")
        
    else:
        print("\n✗ Both benchmarks failed")
        return 1
    
    print(f"\n{'='*80}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

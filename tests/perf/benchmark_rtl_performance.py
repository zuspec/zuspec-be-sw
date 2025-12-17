#!/usr/bin/env python3
"""
Performance Benchmark: Python RTL Execution vs C Code Generation

Compares Python execution of RTL models (@comb/@sync) with generated C code
across various complexity levels.

Benchmark Categories:
1. Simple Combinational Logic (single ALU operation)
2. Multi-stage Combinational Pipeline (cascaded logic)
3. Synchronous Counter (state update)
4. Mixed Sync/Comb Logic (registered ALU)
5. Complex Combinational (multiple operations)
"""

import time
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple
import zuspec.dataclasses as zdc
from zuspec.be.sw import CGenerator, CCompiler


# =============================================================================
# Benchmark 1: Simple Combinational Logic
# =============================================================================

@zdc.dataclass
class SimpleALU(zdc.Component):
    """Simple XOR ALU - baseline combinational logic"""
    a : zdc.bit16 = zdc.input()
    b : zdc.bit16 = zdc.input()
    result : zdc.bit16 = zdc.output()
    
    @zdc.comb
    def _alu_logic(self):
        self.result = self.a ^ self.b


def benchmark_simple_alu_python(iterations: int) -> float:
    """Benchmark Python execution of simple ALU"""
    alu = SimpleALU()
    
    start = time.perf_counter()
    for i in range(iterations):
        alu.a = i & 0xFFFF
        alu.b = (i * 2) & 0xFFFF
        # Comb process evaluates automatically
        _ = alu.result
    end = time.perf_counter()
    
    return end - start


def benchmark_simple_alu_c(iterations: int, tmpdir: Path) -> Tuple[float, float]:
    """Benchmark C execution of simple ALU"""
    factory = zdc.DataModelFactory()
    ctx = factory.build(SimpleALU)
    
    # Generate C code
    gen_start = time.perf_counter()
    generator = CGenerator(output_dir=str(tmpdir))
    all_sources = generator.generate(ctx)
    # Filter out main.c - we'll provide our own benchmark harness
    sources = [s for s in all_sources if not s.name.endswith('main.c')]
    gen_time = time.perf_counter() - gen_start
    
    # Create benchmark harness
    test_c = tmpdir / "bench_simple_alu.c"
    test_c.write_text(f"""
#include "simplealu.h"
#include <stdio.h>
#include <time.h>

int main() {{
    SimpleALU alu;
    zsp_init_ctxt_t ctxt;
    SimpleALU_init(&ctxt, &alu, "alu", NULL);
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < {iterations}; i++) {{
        alu.a = i & 0xFFFF;
        alu.b = (i * 2) & 0xFFFF;
        SimpleALU__alu_logic(&alu);
        volatile int32_t result = alu.result;
    }}
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("TIME: %.9f\\n", elapsed);
    return 0;
}}
""")
    
    # Compile
    compiler = CCompiler(output_dir=tmpdir)
    executable = tmpdir / "bench_simple_alu"
    sources.append(test_c)
    
    comp_start = time.perf_counter()
    compile_result = compiler.compile(sources, executable)
    comp_time = time.perf_counter() - comp_start
    
    if not compile_result.success:
        print(f"\nCompilation failed!")
        print(f"STDERR:\n{compile_result.stderr}")
        raise RuntimeError(f"Compilation failed: {compile_result.stderr}")
    
    # Run
    result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
    exec_time = float(result.stdout.split("TIME: ")[1].strip())
    
    return exec_time, gen_time + comp_time


# =============================================================================
# Benchmark 2: Multi-stage Combinational Pipeline
# =============================================================================

@zdc.dataclass
class CombPipeline(zdc.Component):
    """3-stage combinational pipeline"""
    input_val : zdc.bit16 = zdc.input()
    output_val : zdc.bit16 = zdc.output()
    
    stage1 : zdc.bit16 = zdc.field()
    stage2 : zdc.bit16 = zdc.field()
    
    @zdc.comb
    def _compute_stage1(self):
        """First stage: multiply by 3"""
        self.stage1 = (self.input_val * 3) & 0xFFFF
    
    @zdc.comb
    def _compute_stage2(self):
        """Second stage: add 7"""
        self.stage2 = (self.stage1 + 7) & 0xFFFF
    
    @zdc.comb
    def _compute_output(self):
        """Third stage: XOR with constant"""
        self.output_val = (self.stage2 ^ 0xAAAA) & 0xFFFF


def benchmark_pipeline_python(iterations: int) -> float:
    """Benchmark Python execution of combinational pipeline"""
    pipe = CombPipeline()
    
    start = time.perf_counter()
    for i in range(iterations):
        pipe.input_val = i & 0xFFFF
        # Comb processes evaluate automatically
        _ = pipe.output_val
    end = time.perf_counter()
    
    return end - start


def benchmark_pipeline_c(iterations: int, tmpdir: Path) -> Tuple[float, float]:
    """Benchmark C execution of combinational pipeline"""
    factory = zdc.DataModelFactory()
    ctx = factory.build(CombPipeline)
    
    gen_start = time.perf_counter()
    generator = CGenerator(output_dir=str(tmpdir))
    all_sources = generator.generate(ctx)
    # Filter out main.c - we'll provide our own benchmark harness
    sources = [s for s in all_sources if not s.name.endswith('main.c')]
    gen_time = time.perf_counter() - gen_start
    
    test_c = tmpdir / "bench_pipeline.c"
    test_c.write_text(f"""
#include "combpipeline.h"
#include <stdio.h>
#include <time.h>

int main() {{
    CombPipeline pipe;
    zsp_init_ctxt_t ctxt;
    CombPipeline_init(&ctxt, &pipe, "pipe", NULL);
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < {iterations}; i++) {{
        pipe.input_val = i & 0xFFFF;
        CombPipeline__compute_stage1(&pipe);
        CombPipeline__compute_stage2(&pipe);
        CombPipeline__compute_output(&pipe);
        volatile int32_t result = pipe.output_val;
    }}
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("TIME: %.9f\\n", elapsed);
    return 0;
}}
""")
    
    compiler = CCompiler(output_dir=tmpdir)
    executable = tmpdir / "bench_pipeline"
    sources.append(test_c)
    
    comp_start = time.perf_counter()
    compile_result = compiler.compile(sources, executable)
    comp_time = time.perf_counter() - comp_start
    
    if not compile_result.success:
        print(f"\nCompilation failed!")
        print(f"STDERR:\n{compile_result.stderr}")
        raise RuntimeError(f"Compilation failed: {compile_result.stderr}")
    
    result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
    exec_time = float(result.stdout.split("TIME: ")[1].strip())
    
    return exec_time, gen_time + comp_time


# =============================================================================
# Benchmark 3: Synchronous Counter
# =============================================================================

@zdc.dataclass
class Counter(zdc.Component):
    """Simple counter with sync process"""
    clock : zdc.bit = zdc.input()
    reset : zdc.bit = zdc.input()
    count : zdc.bit16 = zdc.output()
    
    @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
    def _counter(self):
        if self.reset:
            self.count = 0
        else:
            self.count = (self.count + 1) & 0xFFFF


def benchmark_counter_python(iterations: int) -> float:
    """Benchmark Python execution of counter"""
    counter = Counter()
    counter.reset = 1
    # Manually call sync process for init
    counter._counter.method(counter)
    counter.reset = 0
    
    start = time.perf_counter()
    for i in range(iterations):
        counter.clock = i & 1
        # Manually call sync process
        counter._counter.method(counter)
        _ = counter.count
    end = time.perf_counter()
    
    return end - start


def benchmark_counter_c(iterations: int, tmpdir: Path) -> Tuple[float, float]:
    """Benchmark C execution of counter"""
    factory = zdc.DataModelFactory()
    ctx = factory.build(Counter)
    
    gen_start = time.perf_counter()
    generator = CGenerator(output_dir=str(tmpdir))
    all_sources = generator.generate(ctx)
    # Filter out main.c - we'll provide our own benchmark harness
    sources = [s for s in all_sources if not s.name.endswith('main.c')]
    gen_time = time.perf_counter() - gen_start
    
    test_c = tmpdir / "bench_counter.c"
    test_c.write_text(f"""
#include "counter.h"
#include <stdio.h>
#include <time.h>

int main() {{
    Counter counter;
    zsp_init_ctxt_t ctxt;
    Counter_init(&ctxt, &counter, "counter", NULL);
    
    counter.reset = 1;
    Counter__counter(&counter);
    counter.reset = 0;
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < {iterations}; i++) {{
        counter.clock = i & 1;
        Counter__counter(&counter);
        volatile int32_t result = counter.count;
    }}
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("TIME: %.9f\\n", elapsed);
    return 0;
}}
""")
    
    compiler = CCompiler(output_dir=tmpdir)
    executable = tmpdir / "bench_counter"
    sources.append(test_c)
    
    comp_start = time.perf_counter()
    compile_result = compiler.compile(sources, executable)
    comp_time = time.perf_counter() - comp_start
    
    if not compile_result.success:
        print(f"\nCompilation failed!")
        print(f"STDERR:\n{compile_result.stderr}")
        raise RuntimeError(f"Compilation failed: {compile_result.stderr}")
    
    result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
    exec_time = float(result.stdout.split("TIME: ")[1].strip())
    
    return exec_time, gen_time + comp_time


# =============================================================================
# Benchmark 4: Mixed Sync/Comb (Registered ALU)
# =============================================================================

@zdc.dataclass
class RegisteredALU(zdc.Component):
    """ALU with registered output"""
    clock : zdc.bit = zdc.input()
    reset : zdc.bit = zdc.input()
    a : zdc.bit16 = zdc.input()
    b : zdc.bit16 = zdc.input()
    result : zdc.bit16 = zdc.output()
    alu_out : zdc.bit16 = zdc.field()
    
    @zdc.comb
    def _alu_logic(self):
        self.alu_out = self.a ^ self.b
    
    @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
    def _output_reg(self):
        if self.reset:
            self.result = 0
        else:
            self.result = self.alu_out


def benchmark_registered_alu_python(iterations: int) -> float:
    """Benchmark Python execution of registered ALU"""
    alu = RegisteredALU()
    alu.reset = 1
    # Comb evaluates automatically, but sync needs manual call
    alu._output_reg.method(alu)
    alu.reset = 0
    
    start = time.perf_counter()
    for i in range(iterations):
        alu.a = i & 0xFFFF
        alu.b = (i * 2) & 0xFFFF
        alu.clock = i & 1
        # Comb evaluates automatically, sync needs manual call
        alu._output_reg.method(alu)
        _ = alu.result
    end = time.perf_counter()
    
    return end - start


def benchmark_registered_alu_c(iterations: int, tmpdir: Path) -> Tuple[float, float]:
    """Benchmark C execution of registered ALU"""
    factory = zdc.DataModelFactory()
    ctx = factory.build(RegisteredALU)
    
    gen_start = time.perf_counter()
    generator = CGenerator(output_dir=str(tmpdir))
    all_sources = generator.generate(ctx)
    # Filter out main.c - we'll provide our own benchmark harness
    sources = [s for s in all_sources if not s.name.endswith('main.c')]
    gen_time = time.perf_counter() - gen_start
    
    test_c = tmpdir / "bench_registered_alu.c"
    test_c.write_text(f"""
#include "registeredalu.h"
#include <stdio.h>
#include <time.h>

int main() {{
    RegisteredALU alu;
    zsp_init_ctxt_t ctxt;
    RegisteredALU_init(&ctxt, &alu, "alu", NULL);
    
    alu.reset = 1;
    RegisteredALU__alu_logic(&alu);
    RegisteredALU__output_reg(&alu);
    alu.reset = 0;
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < {iterations}; i++) {{
        alu.a = i & 0xFFFF;
        alu.b = (i * 2) & 0xFFFF;
        alu.clock = i & 1;
        RegisteredALU__alu_logic(&alu);
        RegisteredALU__output_reg(&alu);
        volatile int32_t result = alu.result;
    }}
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("TIME: %.9f\\n", elapsed);
    return 0;
}}
""")
    
    compiler = CCompiler(output_dir=tmpdir)
    executable = tmpdir / "bench_registered_alu"
    sources.append(test_c)
    
    comp_start = time.perf_counter()
    compile_result = compiler.compile(sources, executable)
    comp_time = time.perf_counter() - comp_start
    
    if not compile_result.success:
        print(f"\nCompilation failed!")
        print(f"STDERR:\n{compile_result.stderr}")
        raise RuntimeError(f"Compilation failed: {compile_result.stderr}")
    
    result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
    exec_time = float(result.stdout.split("TIME: ")[1].strip())
    
    return exec_time, gen_time + comp_time


# =============================================================================
# Benchmark 5: Complex Combinational Logic
# =============================================================================

@zdc.dataclass
class ComplexALU(zdc.Component):
    """Complex ALU with multiple operations"""
    a : zdc.bit16 = zdc.input()
    b : zdc.bit16 = zdc.input()
    c : zdc.bit16 = zdc.input()
    op : zdc.bit = zdc.input()
    result : zdc.bit16 = zdc.output()
    
    temp1 : zdc.bit16 = zdc.field()
    temp2 : zdc.bit16 = zdc.field()
    
    @zdc.comb
    def _stage1(self):
        """First computation stage"""
        self.temp1 = ((self.a + self.b) * 3) & 0xFFFF
    
    @zdc.comb
    def _stage2(self):
        """Second computation stage"""
        self.temp2 = ((self.b ^ self.c) + 7) & 0xFFFF
    
    @zdc.comb
    def _final(self):
        """Final mux and computation"""
        if self.op:
            self.result = (self.temp1 & self.temp2) & 0xFFFF
        else:
            self.result = (self.temp1 | self.temp2) & 0xFFFF


def benchmark_complex_alu_python(iterations: int) -> float:
    """Benchmark Python execution of complex ALU"""
    alu = ComplexALU()
    
    start = time.perf_counter()
    for i in range(iterations):
        alu.a = i & 0xFFFF
        alu.b = (i * 2) & 0xFFFF
        alu.c = (i * 3) & 0xFFFF
        alu.op = i & 1
        # Comb processes evaluate automatically
        _ = alu.result
    end = time.perf_counter()
    
    return end - start


def benchmark_complex_alu_c(iterations: int, tmpdir: Path) -> Tuple[float, float]:
    """Benchmark C execution of complex ALU"""
    factory = zdc.DataModelFactory()
    ctx = factory.build(ComplexALU)
    
    gen_start = time.perf_counter()
    generator = CGenerator(output_dir=str(tmpdir))
    all_sources = generator.generate(ctx)
    # Filter out main.c - we'll provide our own benchmark harness
    sources = [s for s in all_sources if not s.name.endswith('main.c')]
    gen_time = time.perf_counter() - gen_start
    
    test_c = tmpdir / "bench_complex_alu.c"
    test_c.write_text(f"""
#include "complexalu.h"
#include <stdio.h>
#include <time.h>

int main() {{
    ComplexALU alu;
    zsp_init_ctxt_t ctxt;
    ComplexALU_init(&ctxt, &alu, "alu", NULL);
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int i = 0; i < {iterations}; i++) {{
        alu.a = i & 0xFFFF;
        alu.b = (i * 2) & 0xFFFF;
        alu.c = (i * 3) & 0xFFFF;
        alu.op = i & 1;
        ComplexALU__stage1(&alu);
        ComplexALU__stage2(&alu);
        ComplexALU__final(&alu);
        volatile int32_t result = alu.result;
    }}
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + 
                     (end.tv_nsec - start.tv_nsec) / 1e9;
    printf("TIME: %.9f\\n", elapsed);
    return 0;
}}
""")
    
    compiler = CCompiler(output_dir=tmpdir)
    executable = tmpdir / "bench_complex_alu"
    sources.append(test_c)
    
    comp_start = time.perf_counter()
    compile_result = compiler.compile(sources, executable)
    comp_time = time.perf_counter() - comp_start
    
    if not compile_result.success:
        print(f"\nCompilation failed!")
        print(f"STDERR:\n{compile_result.stderr}")
        raise RuntimeError(f"Compilation failed: {compile_result.stderr}")
    
    result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
    exec_time = float(result.stdout.split("TIME: ")[1].strip())
    
    return exec_time, gen_time + comp_time


# =============================================================================
# Main Benchmark Runner
# =============================================================================

def run_benchmark(name: str, python_func, c_func, iterations: int, tmpdir: Path):
    """Run a single benchmark and return results"""
    print(f"\n{'='*70}")
    print(f"Benchmark: {name}")
    print(f"Iterations: {iterations:,}")
    print(f"{'='*70}")
    
    # Run Python benchmark
    print("Running Python benchmark...", end=" ", flush=True)
    py_time = python_func(iterations)
    py_throughput = iterations / py_time
    print(f"Done ({py_time:.6f}s)")
    
    # Run C benchmark
    print("Running C benchmark...", end=" ", flush=True)
    c_exec_time, c_overhead_time = c_func(iterations, tmpdir)
    c_throughput = iterations / c_exec_time
    print(f"Done ({c_exec_time:.6f}s)")
    
    # Calculate speedup
    speedup = py_time / c_exec_time
    
    return {
        'name': name,
        'iterations': iterations,
        'python_time': py_time,
        'python_throughput': py_throughput,
        'c_exec_time': c_exec_time,
        'c_overhead_time': c_overhead_time,
        'c_total_time': c_exec_time + c_overhead_time,
        'c_throughput': c_throughput,
        'speedup': speedup
    }


def print_results_table(results: list):
    """Print formatted results table"""
    print(f"\n{'='*100}")
    print("BENCHMARK RESULTS SUMMARY")
    print(f"{'='*100}")
    
    print(f"\n{'Benchmark':<25} {'Iterations':>12} {'Python (s)':>12} {'C Exec (s)':>12} {'Speedup':>10}")
    print(f"{'-'*25} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")
    
    for r in results:
        print(f"{r['name']:<25} {r['iterations']:>12,} {r['python_time']:>12.6f} "
              f"{r['c_exec_time']:>12.6f} {r['speedup']:>10.2f}x")
    
    print(f"\n{'='*100}")
    print("THROUGHPUT COMPARISON (ops/second)")
    print(f"{'='*100}")
    
    print(f"\n{'Benchmark':<25} {'Python':>15} {'C':>15} {'Improvement':>12}")
    print(f"{'-'*25} {'-'*15} {'-'*15} {'-'*12}")
    
    for r in results:
        print(f"{r['name']:<25} {r['python_throughput']:>15,.0f} "
              f"{r['c_throughput']:>15,.0f} {r['speedup']:>11.2f}x")
    
    # Statistics
    avg_speedup = sum(r['speedup'] for r in results) / len(results)
    min_speedup = min(r['speedup'] for r in results)
    max_speedup = max(r['speedup'] for r in results)
    
    print(f"\n{'='*100}")
    print("STATISTICS")
    print(f"{'='*100}")
    print(f"Average Speedup: {avg_speedup:>6.2f}x")
    print(f"Minimum Speedup: {min_speedup:>6.2f}x")
    print(f"Maximum Speedup: {max_speedup:>6.2f}x")
    print(f"\n{'='*100}")


def main():
    """Main benchmark execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark RTL Python vs C performance')
    parser.add_argument('--iterations', type=int, default=1000000,
                       help='Number of iterations per benchmark (default: 1M)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick benchmarks (100K iterations)')
    args = parser.parse_args()
    
    iterations = 100000 if args.quick else args.iterations
    
    print(f"\n{'='*100}")
    print("RTL PERFORMANCE BENCHMARK: Python vs C")
    print(f"{'='*100}")
    print(f"Iterations per benchmark: {iterations:,}")
    print(f"{'='*100}")
    
    results = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Run benchmarks
        benchmarks = [
            ("Simple Combinational", benchmark_simple_alu_python, benchmark_simple_alu_c),
            ("Multi-stage Pipeline", benchmark_pipeline_python, benchmark_pipeline_c),
            ("Synchronous Counter", benchmark_counter_python, benchmark_counter_c),
            ("Mixed Sync/Comb", benchmark_registered_alu_python, benchmark_registered_alu_c),
            ("Complex Combinational", benchmark_complex_alu_python, benchmark_complex_alu_c),
        ]
        
        for name, py_func, c_func in benchmarks:
            bench_tmpdir = tmpdir / name.lower().replace(" ", "_").replace("/", "_")
            bench_tmpdir.mkdir()
            result = run_benchmark(name, py_func, c_func, iterations, bench_tmpdir)
            results.append(result)
    
    # Print results
    print_results_table(results)
    
    # Save results to file
    results_file = Path("RTL_PERFORMANCE_RESULTS.md")
    with open(results_file, "w") as f:
        f.write("# RTL Performance Benchmark Results\n\n")
        f.write(f"**Date:** 2025-12-17\n")
        f.write(f"**Iterations:** {iterations:,} per benchmark\n\n")
        f.write("## Results Summary\n\n")
        f.write("| Benchmark | Python (s) | C Exec (s) | Speedup |\n")
        f.write("|-----------|------------|------------|----------|\n")
        for r in results:
            f.write(f"| {r['name']} | {r['python_time']:.6f} | "
                   f"{r['c_exec_time']:.6f} | **{r['speedup']:.2f}x** |\n")
        
        avg_speedup = sum(r['speedup'] for r in results) / len(results)
        f.write(f"\n**Average Speedup:** {avg_speedup:.2f}x\n")
    
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()

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
Compare Pure Python vs Theoretical C Performance for RV64I Model

Since the RV64I transfer-function model is implemented as a pure Python interpreter
with async/await and dictionary-based memory, this script:
1. Runs the Python benchmark to get actual measurements
2. Provides theoretical C performance estimates based on typical speedup ratios
3. Generates a comparison table

Note: The RV64I model is designed as a functional model and not optimized for
code generation. A true C version would require significant refactoring.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

def run_python_benchmark(iterations: int):
    """Run the Python benchmark and capture results."""
    print("=" * 70)
    print("Running Python Benchmark...")
    print("=" * 70)
    
    cmd = [
        sys.executable,
        str(REPO_ROOT / "tests" / "perf" / "benchmark_rv64_model.py"),
        "--iterations", str(iterations)
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    
    if result.returncode != 0:
        print(f"Error running benchmark: {result.stderr}")
        return None
    
    # Parse the output to extract MIPS values from the summary table
    output = result.stdout
    benchmarks = {}
    
    in_summary = False
    for line in output.split('\n'):
        if 'Summary' in line:
            in_summary = True
        elif in_summary and line.startswith('-'):
            continue
        elif in_summary and line.strip():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    # Last column is MIPS value, everything before last 2 columns is name
                    name = ' '.join(parts[:-2])
                    mips = float(parts[-1])
                    if name and name != 'Average' and name != 'Benchmark':
                        benchmarks[name] = mips
                except (ValueError, IndexError):
                    pass
    
    return benchmarks, output

def estimate_c_performance(python_benchmarks):
    """
    Estimate C performance based on typical Python-to-C speedup ratios.
    
    Conservative estimates for interpreted models:
    - Simple loops with branches: 50-100x speedup
    - ALU operations: 30-60x speedup  
    - Memory operations: 20-40x speedup (async overhead)
    - Mixed workloads: 30-50x speedup
    - Sustained execution: 40-70x speedup
    """
    
    speedup_factors = {
        'Tight Loop': 75,          # Branch-heavy, benefits most from compilation
        'ALU Intensive': 45,       # Arithmetic ops compile well
        'Memory Intensive': 30,    # Memory dict lookups -> C arrays
        'Fibonacci': 40,           # Mixed workload
        'Sustained': 55,           # Long-running benefits from no GC/interpreter
    }
    
    c_estimates = {}
    for name, python_mips in python_benchmarks.items():
        factor = speedup_factors.get(name, 40)  # Default 40x
        c_estimates[name] = python_mips * factor
    
    return c_estimates, speedup_factors

def print_comparison_table(python_benchmarks, c_estimates, speedup_factors):
    """Print a formatted comparison table."""
    print("\n" + "=" * 80)
    print("RV64I MODEL PERFORMANCE COMPARISON: Python vs Theoretical C")
    print("=" * 80)
    print()
    print(f"{'Benchmark':<20} {'Python (MIPS)':>15} {'Est. C (MIPS)':>15} {'Speedup':>10}")
    print("-" * 80)
    
    for name in ['Tight Loop', 'ALU Intensive', 'Memory Intensive', 'Fibonacci', 'Sustained']:
        if name in python_benchmarks:
            py_mips = python_benchmarks[name]
            c_mips = c_estimates[name]
            speedup = speedup_factors[name]
            print(f"{name:<20} {py_mips:>15.2f} {c_mips:>15.2f} {speedup:>9.0f}x")
    
    # Calculate averages
    if python_benchmarks:
        avg_py = sum(python_benchmarks.values()) / len(python_benchmarks)
        avg_c = sum(c_estimates.values()) / len(c_estimates)
        avg_speedup = avg_c / avg_py if avg_py > 0 else 0
        
        print("-" * 80)
        print(f"{'Average':<20} {avg_py:>15.2f} {avg_c:>15.2f} {avg_speedup:>9.0f}x")
    
    print("=" * 80)
    print()
    print("NOTES:")
    print("------")
    print("* Python measurements are actual benchmark results")
    print("* C estimates are theoretical based on typical Python-to-C speedup ratios")
    print("* Actual C performance would depend on:")
    print("  - Quality of generated C code")
    print("  - Compiler optimizations (-O2/-O3)")
    print("  - Memory model implementation (dict -> arrays)")
    print("  - Async overhead elimination")
    print("  - CPU architecture and cache behavior")
    print()
    print("SPEEDUP FACTORS EXPLAINED:")
    print("---------------------------")
    print("* Tight Loop (75x): Branch-heavy code benefits most from compilation")
    print("* ALU Intensive (45x): Integer arithmetic compiles efficiently")
    print("* Memory Intensive (30x): Dict lookups -> C arrays, but still has overhead")
    print("* Fibonacci (40x): Mixed workload with moderate speedup")
    print("* Sustained (55x): Long-running eliminates GC/interpreter overhead")
    print()
    print("COMPARISON CONTEXT:")
    print("-------------------")
    print("For reference, typical performance ranges:")
    print("* Python interpreted ISA model: 1-2 MIPS")
    print("* C compiled ISA model: 50-100 MIPS")
    print("* Optimized JIT ISA model: 100-500 MIPS")
    print("* Hardware RV64I core: 1000-5000+ MIPS (1-5+ GHz)")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description="Compare Python vs theoretical C performance for RV64I model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --iterations 100000
  %(prog)s --iterations 1000000 --show-python-output
        """
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100000,
        help="Number of iterations for tight loop benchmark (default: 100000)"
    )
    parser.add_argument(
        "--show-python-output",
        action="store_true",
        help="Show full Python benchmark output"
    )
    
    args = parser.parse_args()
    
    # Run Python benchmark
    result = run_python_benchmark(args.iterations)
    if result is None:
        print("Failed to run Python benchmark")
        return 1
    
    python_benchmarks, output = result
    
    if args.show_python_output:
        print("\nFull Python Benchmark Output:")
        print("-" * 70)
        print(output)
    
    if not python_benchmarks:
        print("Failed to parse benchmark results")
        return 1
    
    # Estimate C performance
    c_estimates, speedup_factors = estimate_c_performance(python_benchmarks)
    
    # Print comparison table
    print_comparison_table(python_benchmarks, c_estimates, speedup_factors)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

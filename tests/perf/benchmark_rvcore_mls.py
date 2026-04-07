#!/usr/bin/env python3
"""
Benchmark: RVCore MLS C-backend instruction throughput.

Measures instructions-per-second and "cycles"-per-second for the
MLS-compiled RVCore model running tight loops of RV32I instructions.

Metrics reported:
  - Raw IPS   : instructions per second as seen by the icache callback
  - Effective IPS: correcting for the NOP drain instruction at end
  - Python↔C callback overhead

Run with:
    python packages/zuspec-be-sw/tests/perf/benchmark_rvcore_mls.py
"""

import sys
import time
import ctypes
import tempfile
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "packages" / "zuspec-dataclasses" / "src"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "zuspec-be-sw" / "src"))
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from zuspec.be.sw.co_obj_factory import CObjFactory
from org.zuspec.example.mls.riscv.rv_core import RVCore


# ---------------------------------------------------------------------------
# Instruction encoders
# ---------------------------------------------------------------------------

def r_enc(funct7, rs2, rs1, funct3, rd):
    """R-type: ADD/SUB/AND/OR/XOR."""
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0x33

def i_enc(imm, rs1, funct3, rd, opcode):
    """I-type: ADDI/LOAD/JALR."""
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

# NOP = ADDI x0, x0, 0
NOP    = i_enc(0, 0, 0, 0, 0x13)
# ADD x1, x2, x3
ADD    = r_enc(0, 3, 2, 0, 1)
# ADDI x1, x1, 1  (tight increment loop body)
ADDI1  = i_enc(1, 1, 0, 1, 0x13)


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------

def build_icache_counter(fac, proxy, program: list, n_warmup: int = 0):
    """Return (callback_fn, stats_dict).

    *program* is a list of instruction encodings served round-robin.
    After *n_warmup* instructions, timing starts.  The callback counts
    fetches and stops after a fixed number.
    """
    stats = {
        "fetches": 0,
        "t_start": None,
        "t_end": None,
        "target": None,
    }
    prog = program

    def cb(addr: int) -> int:
        n = stats["fetches"]
        if n == n_warmup:
            stats["t_start"] = time.perf_counter()
        stats["fetches"] = n + 1
        if stats["target"] is not None and n >= stats["target"]:
            stats["t_end"] = time.perf_counter()
            proxy.request_halt()
            return NOP
        return prog[addr // 4 % len(prog)]

    fac.bind_callable(proxy, "icache", cb)
    return stats


def run_bench(fac, proxy, program, n_instructions, label, n_warmup=1000):
    """Execute *n_instructions* via *program*, print results."""
    stats = build_icache_counter(fac, proxy, program, n_warmup)
    stats["target"] = n_warmup + n_instructions

    t0 = time.perf_counter()
    proxy.run()
    t_wall = time.perf_counter() - t0

    fetches = stats["fetches"]
    if stats["t_start"] and stats["t_end"]:
        elapsed = stats["t_end"] - stats["t_start"]
    else:
        elapsed = t_wall

    ips = n_instructions / elapsed if elapsed > 0 else 0
    mips = ips / 1e6

    print(f"  {label:<30s}: {mips:7.2f} MIPS  "
          f"({n_instructions:,} insns in {elapsed*1000:.1f} ms, "
          f"{fetches:,} total fetches)")
    return mips


# ---------------------------------------------------------------------------
# Callback overhead measurement
# ---------------------------------------------------------------------------

def measure_callback_overhead(fac, proxy, n=200_000):
    """Measure pure Python↔C callback overhead."""
    calls = [0]
    t_calls = []

    def cb(addr: int) -> int:
        calls[0] += 1
        t_calls.append(time.perf_counter())
        if calls[0] >= n:
            proxy.request_halt()
        return NOP

    fac.bind_callable(proxy, "icache", cb)
    proxy.run()

    if len(t_calls) >= 2:
        total = t_calls[-1] - t_calls[0]
        avg_us = total / len(t_calls) * 1e6
        cb_per_sec = len(t_calls) / total
        print(f"  Callback overhead (NOP loop) : {avg_us:.2f} µs/call  "
              f"({cb_per_sec/1e6:.2f} Mcalls/s, N={len(t_calls):,})")
    return calls[0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="rvcore_bench_"))
    try:
        print("=== RVCore MLS C-backend Benchmark ===\n")
        print("Compiling RVCore model (first run includes compile time)...")
        t_compile = time.perf_counter()
        fac = CObjFactory(cache_dir=tmpdir)
        proxy = fac.mkComponent(RVCore)
        print(f"  Compile + load : {(time.perf_counter()-t_compile)*1000:.0f} ms\n")

        N = 500_000  # instructions per benchmark run

        print("--- Instruction throughput (icache is Python callback) ---")
        run_bench(fac, proxy, [NOP],   N, "NOP stream (ADDI x0,x0,0)")
        run_bench(fac, proxy, [ADD],   N, "ADD  x1,x2,x3 stream")
        run_bench(fac, proxy, [ADDI1], N, "ADDI x1,x1,1 stream")

        # Varied program: alternating ADD + ADDI
        run_bench(fac, proxy, [ADD, ADDI1], N, "ADD / ADDI alternating")

        print()
        print("--- Python callback overhead ---")
        measure_callback_overhead(fac, proxy, n=200_000)

        print()
        print("--- Notes ---")
        print("  Every instruction fetch crosses C→Python (ctypes CFUNCTYPE).")
        print("  Throughput is dominated by that boundary, not instruction logic.")
        print("  A native C icache (no Python callback) would be ~10-100× faster.")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()

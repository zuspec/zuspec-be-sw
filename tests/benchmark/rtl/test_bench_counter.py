"""
Counter throughput benchmarks.

Measures Mcycles/sec for:
  - zuspec-be-sw compiled C (primary)
  - iverilog (baseline, if available)
  - Verilator (comparison, if available)

Run with:
    pytest tests/benchmark/bench_counter.py --run-benchmarks -v
"""
from __future__ import annotations

import ctypes
import sys
import time
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).parents[5] / "examples"
_COUNTER_DIR = _EXAMPLES / "01_counter"

# ── Load Counter class ──────────────────────────────────────────────────────

if str(_COUNTER_DIR) not in sys.path:
    sys.path.insert(0, str(_COUNTER_DIR))

from counter import Counter  # noqa: E402

# ── Cycle counts to benchmark ────────────────────────────────────────────────

N_CYCLES = [1_000_000, 10_000_000, 100_000_000]

# ── Compiled-C fixtures ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def counter_so(tmp_path_factory):
    from zuspec.be.sw import compile_and_load
    outdir = tmp_path_factory.mktemp("counter_bench")
    return compile_and_load(Counter, outdir)


# ── Compiled-C benchmark ─────────────────────────────────────────────────────


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", N_CYCLES, ids=[f"{n//1_000_000}M" for n in N_CYCLES])
def test_bench_counter_c(counter_so, benchmark, n):
    """Measure compiled-C clock-edge throughput for Counter."""
    lib, State = counter_so
    lib.Counter_init.argtypes = [ctypes.POINTER(State)]
    lib.Counter_init.restype = None
    lib.Counter_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.Counter_clock_edge.restype = None

    st = State()
    lib.Counter_init(ctypes.byref(st))
    st.reset = 1
    lib.Counter_clock_edge(ctypes.byref(st))
    st.reset = 0
    st.enable = 1

    def _run_n():
        for _ in range(n):
            lib.Counter_clock_edge(ctypes.byref(st))

    result = benchmark(_run_n)
    # Annotate with Mcycles/sec for the report
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info["Mcycles_per_sec"] = n / mean_s / 1e6
    benchmark.extra_info["component"] = "Counter"
    benchmark.extra_info["simulator"] = "compiled-C"
    benchmark.extra_info["n_cycles"] = n


# ── iverilog benchmark ────────────────────────────────────────────────────────


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [1_000_000], ids=["1M"])
def test_bench_counter_iverilog(iverilog_path, benchmark, n, tmp_path):
    """Measure iverilog simulation throughput for Counter."""
    from .conftest import iverilog_bench_cycles

    tb = _COUNTER_DIR / "bench" / "tb_bench_counter.sv"
    dut = _COUNTER_DIR / "counter.sv"

    def _run():
        return iverilog_bench_cycles(tb, dut, n, tmp_path, iverilog_path)

    result = benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info["Mcycles_per_sec"] = n / mean_s / 1e6
    benchmark.extra_info["component"] = "Counter"
    benchmark.extra_info["simulator"] = "iverilog"
    benchmark.extra_info["n_cycles"] = n


# ── Verilator benchmark ───────────────────────────────────────────────────────


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [1_000_000, 10_000_000], ids=["1M", "10M"])
def test_bench_counter_verilator(verilator_path, benchmark, n, tmp_path):
    """Measure Verilator simulation throughput for Counter."""
    from .conftest import verilator_bench_cycles

    tb = _COUNTER_DIR / "bench" / "tb_bench_counter.sv"
    dut = _COUNTER_DIR / "counter.sv"

    def _run():
        return verilator_bench_cycles(
            tb, dut, "Counter", n, tmp_path, verilator_path
        )

    result = benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info["Mcycles_per_sec"] = n / mean_s / 1e6
    benchmark.extra_info["component"] = "Counter"
    benchmark.extra_info["simulator"] = "verilator"
    benchmark.extra_info["n_cycles"] = n

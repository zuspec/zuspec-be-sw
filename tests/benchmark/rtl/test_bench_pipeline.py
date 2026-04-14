"""
MultAccPipeline throughput benchmarks — compiled-C vs iverilog vs Verilator.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).parents[5] / "examples"
_PIPE_DIR = _EXAMPLES / "05_pipeline"

if str(_PIPE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPE_DIR))

from pipeline import MultAccPipeline  # noqa: E402

N = 1_000_000


@pytest.fixture(scope="module")
def pipeline_so(tmp_path_factory):
    from zuspec.be.sw import compile_and_load
    return compile_and_load(MultAccPipeline, tmp_path_factory.mktemp("pipeline_bench"))


@pytest.mark.benchmark_test
def test_bench_pipeline_c(pipeline_so, benchmark):
    lib, State = pipeline_so
    lib.MultAccPipeline_init.argtypes = [ctypes.POINTER(State)]
    lib.MultAccPipeline_init.restype = None
    lib.MultAccPipeline_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.MultAccPipeline_clock_edge.restype = None

    st = State()
    lib.MultAccPipeline_init(ctypes.byref(st))
    st.reset = 1
    lib.MultAccPipeline_clock_edge(ctypes.byref(st))
    st.reset = 0

    def _run():
        for _ in range(N):
            lib.MultAccPipeline_clock_edge(ctypes.byref(st))

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=N / mean_s / 1e6,
        component="MultAccPipeline",
        simulator="compiled-C",
        n_cycles=N,
    )


@pytest.mark.benchmark_test
def test_bench_pipeline_iverilog(iverilog_path, benchmark, tmp_path):
    from .conftest import iverilog_bench_cycles
    tb = _PIPE_DIR / "bench" / "tb_bench_mult_acc_pipeline.sv"
    dut = _PIPE_DIR / "mult_acc_pipeline.sv"
    benchmark(
        lambda: iverilog_bench_cycles(tb, dut, N, tmp_path, iverilog_path)
    )
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=N / mean_s / 1e6,
        component="MultAccPipeline",
        simulator="iverilog",
        n_cycles=N,
    )


@pytest.mark.benchmark_test
def test_bench_pipeline_verilator(verilator_path, benchmark, tmp_path):
    from .conftest import verilator_bench_cycles
    tb = _PIPE_DIR / "bench" / "tb_bench_mult_acc_pipeline.sv"
    dut = _PIPE_DIR / "mult_acc_pipeline.sv"
    benchmark(
        lambda: verilator_bench_cycles(
            tb, dut, "MultAccPipeline", N, tmp_path, verilator_path
        )
    )
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=N / mean_s / 1e6,
        component="MultAccPipeline",
        simulator="verilator",
        n_cycles=N,
    )

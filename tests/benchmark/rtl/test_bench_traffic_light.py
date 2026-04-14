"""
TrafficLight throughput benchmarks — compiled-C vs iverilog vs Verilator.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).parents[5] / "examples"
_TL_DIR = _EXAMPLES / "03_traffic_light"

if str(_TL_DIR) not in sys.path:
    sys.path.insert(0, str(_TL_DIR))

from traffic_light import TrafficLight  # noqa: E402

N = 1_000_000


@pytest.fixture(scope="module")
def tl_so(tmp_path_factory):
    from zuspec.be.sw import compile_and_load
    return compile_and_load(TrafficLight, tmp_path_factory.mktemp("tl_bench"))


@pytest.mark.benchmark_test
def test_bench_tl_c(tl_so, benchmark):
    lib, State = tl_so
    lib.TrafficLight_init.argtypes = [ctypes.POINTER(State)]
    lib.TrafficLight_init.restype = None
    lib.TrafficLight_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.TrafficLight_clock_edge.restype = None

    st = State()
    lib.TrafficLight_init(ctypes.byref(st))
    st.reset = 1
    lib.TrafficLight_clock_edge(ctypes.byref(st))
    st.reset = 0

    def _run():
        for _ in range(N):
            lib.TrafficLight_clock_edge(ctypes.byref(st))

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=N / mean_s / 1e6,
        component="TrafficLight",
        simulator="compiled-C",
        n_cycles=N,
    )


@pytest.mark.benchmark_test
def test_bench_tl_iverilog(iverilog_path, benchmark, tmp_path):
    from .conftest import iverilog_bench_cycles
    tb = _TL_DIR / "bench" / "tb_bench_traffic_light.sv"
    dut = _TL_DIR / "traffic_light.sv"
    benchmark(lambda: iverilog_bench_cycles(tb, dut, N, tmp_path, iverilog_path))
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=N / mean_s / 1e6,
        component="TrafficLight",
        simulator="iverilog",
        n_cycles=N,
    )


@pytest.mark.benchmark_test
def test_bench_tl_verilator(verilator_path, benchmark, tmp_path):
    from .conftest import verilator_bench_cycles
    tb = _TL_DIR / "bench" / "tb_bench_traffic_light.sv"
    dut = _TL_DIR / "traffic_light.sv"
    benchmark(
        lambda: verilator_bench_cycles(tb, dut, "TrafficLight", N, tmp_path, verilator_path)
    )
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=N / mean_s / 1e6,
        component="TrafficLight",
        simulator="verilator",
        n_cycles=N,
    )

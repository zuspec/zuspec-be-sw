"""
Native-speed benchmark: compiled-C ``run_cycles()`` vs Verilator.

``run_cycles()`` executes N clock cycles inside a single C call — no Python
overhead per cycle.  This reveals the raw throughput potential of the
zuspec-be-sw compiled model and gives a fair comparison point against
Verilator, which also runs its simulation loop entirely in C++.

Run with:
    pytest tests/benchmark/test_native_speed.py --run-benchmarks -v
    pytest tests/benchmark/test_native_speed.py --run-benchmarks -v \
           --benchmark-json=native_speed.json
    python tests/benchmark/report.py native_speed.json
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).parents[5] / "examples"

# ── helpers ──────────────────────────────────────────────────────────────────


def _setup_counter(lib, State):
    lib.Counter_init.argtypes = [ctypes.POINTER(State)]
    lib.Counter_init.restype = None
    lib.Counter_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.Counter_clock_edge.restype = None
    lib.Counter_run_cycles.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
    lib.Counter_run_cycles.restype = None
    st = State()
    lib.Counter_init(ctypes.byref(st))
    st.reset = 1
    lib.Counter_clock_edge(ctypes.byref(st))
    st.reset = 0
    st.enable = 1
    return st


def _setup_tl(lib, State):
    lib.TrafficLight_init.argtypes = [ctypes.POINTER(State)]
    lib.TrafficLight_init.restype = None
    lib.TrafficLight_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.TrafficLight_clock_edge.restype = None
    lib.TrafficLight_run_cycles.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
    lib.TrafficLight_run_cycles.restype = None
    st = State()
    lib.TrafficLight_init(ctypes.byref(st))
    st.reset = 1
    lib.TrafficLight_clock_edge(ctypes.byref(st))
    st.reset = 0
    return st


def _setup_pipeline(lib, State):
    lib.MultAccPipeline_init.argtypes = [ctypes.POINTER(State)]
    lib.MultAccPipeline_init.restype = None
    lib.MultAccPipeline_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.MultAccPipeline_clock_edge.restype = None
    lib.MultAccPipeline_run_cycles.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
    lib.MultAccPipeline_run_cycles.restype = None
    st = State()
    lib.MultAccPipeline_init(ctypes.byref(st))
    st.reset = 1
    lib.MultAccPipeline_clock_edge(ctypes.byref(st))
    st.reset = 0
    return st


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def counter_so(tmp_path_factory):
    sys.path.insert(0, str(_EXAMPLES / "01_counter"))
    from counter import Counter
    from zuspec.be.sw import compile_and_load
    return compile_and_load(Counter, tmp_path_factory.mktemp("ns_counter"))


@pytest.fixture(scope="module")
def tl_so(tmp_path_factory):
    sys.path.insert(0, str(_EXAMPLES / "03_traffic_light"))
    from traffic_light import TrafficLight
    from zuspec.be.sw import compile_and_load
    return compile_and_load(TrafficLight, tmp_path_factory.mktemp("ns_tl"))


@pytest.fixture(scope="module")
def pipeline_so(tmp_path_factory):
    sys.path.insert(0, str(_EXAMPLES / "05_pipeline"))
    from pipeline import MultAccPipeline
    from zuspec.be.sw import compile_and_load
    return compile_and_load(MultAccPipeline, tmp_path_factory.mktemp("ns_pipeline"))


# ── Parametrize ───────────────────────────────────────────────────────────────

N_SMALL  = 10_000_000    # 10M — used for Verilator (compile overhead amortized)
N_LARGE  = 100_000_000   # 100M — used for compiled-C native

# ── Counter benchmarks ────────────────────────────────────────────────────────


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [N_SMALL, N_LARGE], ids=["10M", "100M"])
def test_native_counter_c_bulk(counter_so, benchmark, n):
    """Counter: bulk run_cycles() — single C call, N cycles, no Python overhead."""
    lib, State = counter_so
    st = _setup_counter(lib, State)

    def _run():
        lib.Counter_run_cycles(ctypes.byref(st), n)
        return st.count

    result = benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=n / mean_s / 1e6,
        component="Counter",
        simulator="compiled-C-bulk",
        n_cycles=n,
    )


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [N_SMALL], ids=["10M"])
def test_native_counter_c_percycle(counter_so, benchmark, n):
    """Counter: per-cycle ctypes calls (Python overhead baseline)."""
    lib, State = counter_so
    st = _setup_counter(lib, State)

    def _run():
        for _ in range(n):
            lib.Counter_clock_edge(ctypes.byref(st))

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=n / mean_s / 1e6,
        component="Counter",
        simulator="compiled-C-percycle",
        n_cycles=n,
    )


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [N_SMALL], ids=["10M"])
def test_native_counter_verilator(verilator_path, benchmark, n, tmp_path):
    """Counter: Verilator — compile once, measure run-only throughput."""
    from .conftest import verilator_precompile
    bench_cpp = _EXAMPLES / "01_counter" / "bench" / "bench_main.cpp"
    dut       = _EXAMPLES / "01_counter" / "counter.sv"
    obj_dir   = tmp_path / "obj_dir"
    binary    = verilator_precompile(
        bench_cpp, dut, "Counter", obj_dir, tmp_path, verilator_path
    )

    def _run():
        subprocess.check_call(
            [str(binary), f"+CYCLES={n}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=n / mean_s / 1e6,
        component="Counter",
        simulator="verilator",
        n_cycles=n,
    )


# ── TrafficLight benchmarks ───────────────────────────────────────────────────


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [N_SMALL, N_LARGE], ids=["10M", "100M"])
def test_native_tl_c_bulk(tl_so, benchmark, n):
    """TrafficLight: bulk run_cycles()."""
    lib, State = tl_so
    st = _setup_tl(lib, State)

    def _run():
        lib.TrafficLight_run_cycles(ctypes.byref(st), n)

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=n / mean_s / 1e6,
        component="TrafficLight",
        simulator="compiled-C-bulk",
        n_cycles=n,
    )


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [N_SMALL], ids=["10M"])
def test_native_tl_verilator(verilator_path, benchmark, n, tmp_path):
    """TrafficLight: Verilator — pre-compiled, run only."""
    from .conftest import verilator_precompile
    bench_cpp = _EXAMPLES / "03_traffic_light" / "bench" / "bench_main.cpp"
    dut       = _EXAMPLES / "03_traffic_light" / "traffic_light.sv"
    obj_dir   = tmp_path / "obj_dir"
    binary    = verilator_precompile(
        bench_cpp, dut, "TrafficLight", obj_dir, tmp_path, verilator_path
    )

    def _run():
        subprocess.check_call(
            [str(binary), f"+CYCLES={n}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=n / mean_s / 1e6,
        component="TrafficLight",
        simulator="verilator",
        n_cycles=n,
    )


# ── MultAccPipeline benchmarks ────────────────────────────────────────────────


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [N_SMALL, N_LARGE], ids=["10M", "100M"])
def test_native_pipeline_c_bulk(pipeline_so, benchmark, n):
    """MultAccPipeline: bulk run_cycles()."""
    lib, State = pipeline_so
    st = _setup_pipeline(lib, State)

    def _run():
        lib.MultAccPipeline_run_cycles(ctypes.byref(st), n)

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=n / mean_s / 1e6,
        component="MultAccPipeline",
        simulator="compiled-C-bulk",
        n_cycles=n,
    )


@pytest.mark.benchmark_test
@pytest.mark.parametrize("n", [N_SMALL], ids=["10M"])
def test_native_pipeline_verilator(verilator_path, benchmark, n, tmp_path):
    """MultAccPipeline: Verilator — pre-compiled, run only."""
    from .conftest import verilator_precompile
    bench_cpp = _EXAMPLES / "05_pipeline" / "bench" / "bench_main.cpp"
    dut       = _EXAMPLES / "05_pipeline" / "mult_acc_pipeline.sv"
    obj_dir   = tmp_path / "obj_dir"
    binary    = verilator_precompile(
        bench_cpp, dut, "MultAccPipeline", obj_dir, tmp_path, verilator_path,
        extra_args=["-Wno-WIDTH", "-Wno-CMPCONST"],
    )

    def _run():
        subprocess.check_call(
            [str(binary), f"+CYCLES={n}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    benchmark.extra_info.update(
        Mcycles_per_sec=n / mean_s / 1e6,
        component="MultAccPipeline",
        simulator="verilator",
        n_cycles=n,
    )

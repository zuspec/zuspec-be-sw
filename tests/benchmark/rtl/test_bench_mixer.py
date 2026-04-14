"""
MixerCore benchmark: compiled-C run_cycles() vs Verilator.

MixerCore is a 32-register cellular-automaton mixer with a run_req/done
handshake.  Two benchmark modes are measured:

  **Bulk** (1 transaction × N cycles):
    - Zuspec C: set inputs, 1 clock_edge call, run_cycles(N+5) — almost no Python overhead.
    - Verilator: +TXNS=1 +KCYCLES=N — pure C++ loop.

  **Multi-txn** (T transactions × K cycles, Python-driven for Zuspec):
    - Zuspec C: Python loop — 2 ctypes calls per transaction (clock_edge + run_cycles).
    - Verilator: +TXNS=T +KCYCLES=K — all in C++.

Run with:
    pytest tests/benchmark/test_bench_mixer.py --run-benchmarks -v
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).parents[5] / "examples"
_MIXER    = _EXAMPLES / "07_mixer"


# ── Fixture ────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def mixer_so(tmp_path_factory):
    sys.path.insert(0, str(_MIXER))
    from mixer import MixerCore
    from zuspec.be.sw import compile_and_load
    return compile_and_load(MixerCore, tmp_path_factory.mktemp("bench_mixer"))


def _setup_mixer(lib, State):
    """Bind ctypes argtypes and return a reset state ready to run."""
    lib.MixerCore_init.argtypes = [ctypes.POINTER(State)]
    lib.MixerCore_init.restype = None
    lib.MixerCore_apply_reset.argtypes = [ctypes.POINTER(State)]
    lib.MixerCore_apply_reset.restype = None
    lib.MixerCore_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.MixerCore_clock_edge.restype = None
    lib.MixerCore_run_cycles.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
    lib.MixerCore_run_cycles.restype = None

    st = State()
    lib.MixerCore_init(ctypes.byref(st))
    lib.MixerCore_apply_reset(ctypes.byref(st))
    return st


# ── Bulk benchmarks (1 large transaction, minimal Python interaction) ──────────

N_BULK = 10_000_000   # 10M mixing cycles per transaction

@pytest.mark.benchmark_test
def test_mixer_c_bulk(mixer_so, benchmark):
    """MixerCore: Zuspec C — 1 transaction × 10M cycles (2 Python calls total)."""
    lib, State = mixer_so
    st = _setup_mixer(lib, State)

    st.data_in  = 0x12345678
    st.n_cycles = N_BULK

    def _run():
        lib.MixerCore_apply_reset(ctypes.byref(st))
        st.run_req = 1
        lib.MixerCore_clock_edge(ctypes.byref(st))   # starts the run
        st.run_req = 0
        lib.MixerCore_run_cycles(ctypes.byref(st), N_BULK + 10)  # wait for done
        assert st.done == 1, "MixerCore did not complete!"
        return st.result

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    total_cycles = N_BULK + 11
    benchmark.extra_info.update(
        Mcycles_per_sec=total_cycles / mean_s / 1e6,
        component="MixerCore",
        simulator="compiled-C-bulk",
        n_cycles=total_cycles,
    )


@pytest.mark.benchmark_test
def test_mixer_verilator_bulk(verilator_path, benchmark, tmp_path):
    """MixerCore: Verilator — 1 transaction × 10M cycles."""
    from .conftest import verilator_precompile
    bench_cpp = _MIXER / "bench" / "bench_main.cpp"
    dut_sv    = _MIXER / "mixer.sv"
    obj_dir   = tmp_path / "obj_dir"
    binary    = verilator_precompile(
        bench_cpp, dut_sv, "MixerCore", obj_dir, tmp_path, verilator_path,
    )

    def _run():
        subprocess.check_call(
            [str(binary), f"+TXNS=1", f"+KCYCLES={N_BULK}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    total_cycles = N_BULK + 15   # approx (reset + guard)
    benchmark.extra_info.update(
        Mcycles_per_sec=total_cycles / mean_s / 1e6,
        component="MixerCore",
        simulator="verilator-bulk",
        n_cycles=total_cycles,
    )


# ── Multi-transaction benchmarks (Python-driven for Zuspec) ───────────────────

N_TXNS  = 10_000   # number of transactions
K_CYCLES = 1_000   # mixing cycles per transaction
# Total mixing work: 10M cycles, split across 10k transactions


@pytest.mark.benchmark_test
def test_mixer_c_multitxn(mixer_so, benchmark):
    """MixerCore: Zuspec C — 10k transactions × 1k cycles (Python-driven handshake)."""
    lib, State = mixer_so
    st = _setup_mixer(lib, State)

    st.data_in  = 0xDEADBEEF
    st.n_cycles = K_CYCLES

    lib.MixerCore_apply_reset(ctypes.byref(st))

    def _run():
        for _ in range(N_TXNS):
            st.run_req = 1
            lib.MixerCore_clock_edge(ctypes.byref(st))
            st.run_req = 0
            lib.MixerCore_run_cycles(ctypes.byref(st), K_CYCLES + 5)

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    total_cycles = N_TXNS * (K_CYCLES + 6)
    benchmark.extra_info.update(
        Mcycles_per_sec=total_cycles / mean_s / 1e6,
        component="MixerCore",
        simulator="compiled-C-multitxn",
        n_cycles=total_cycles,
        n_txns=N_TXNS,
        k_cycles=K_CYCLES,
    )


@pytest.mark.benchmark_test
def test_mixer_verilator_multitxn(verilator_path, benchmark, tmp_path):
    """MixerCore: Verilator — 10k transactions × 1k cycles (C++ loop)."""
    from .conftest import verilator_precompile
    bench_cpp = _MIXER / "bench" / "bench_main.cpp"
    dut_sv    = _MIXER / "mixer.sv"
    obj_dir   = tmp_path / "obj_dir"
    binary    = verilator_precompile(
        bench_cpp, dut_sv, "MixerCore", obj_dir, tmp_path, verilator_path,
    )

    def _run():
        subprocess.check_call(
            [str(binary), f"+TXNS={N_TXNS}", f"+KCYCLES={K_CYCLES}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    total_cycles = N_TXNS * (K_CYCLES + 11)
    benchmark.extra_info.update(
        Mcycles_per_sec=total_cycles / mean_s / 1e6,
        component="MixerCore",
        simulator="verilator-multitxn",
        n_cycles=total_cycles,
        n_txns=N_TXNS,
        k_cycles=K_CYCLES,
    )

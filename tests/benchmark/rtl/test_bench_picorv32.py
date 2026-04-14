"""
PicoRV32 benchmark: Zuspec-compiled C vs. Verilator on original picorv32.v.

Both simulators execute the same 1 000 000-iteration RV32I counting loop
with a simple flat-memory model handled entirely in C/C++.  The
run_req/run_ack handshake used by MixerCore is NOT needed here — the loop
runs until the CPU asserts ``trap``.

Run with:
    pytest tests/benchmark/test_bench_picorv32.py --run-benchmarks -v
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

_REPO     = Path(__file__).parents[4]
_EXAMPLES = _REPO / "examples"
_BENCH    = _EXAMPLES / "08_picorv32_bench"
_PICORV32_SRC = (
    _REPO.parent / "zuspec-example-mls-riscv" / "zpicorv32" / "picorv32.py"
)
_PICORV32_V = (
    _REPO.parent / "zuspec-example-mls-riscv" / "picorv32" / "picorv32.v"
)

# Expected answer from the 16 M iteration loop
_EXPECTED_RESULT = 16_000_000


# ── Shared fixture: build PicoRV32.so + bench_zuspec binary ─────────────────

@pytest.fixture(scope="module")
def zuspec_bench_bin(tmp_path_factory):
    """Compile PicoRV32.so and bench_zuspec; return path to binary."""
    outdir = tmp_path_factory.mktemp("picorv32_bench")

    # Import zpicorv32 (adds its directory to sys.path)
    sys.path.insert(0, str(_PICORV32_SRC.parent))
    from picorv32 import PicoRV32  # noqa: PLC0415

    from zuspec.be.sw import compile_and_load
    _lib, _State = compile_and_load(PicoRV32, outdir)

    # Copy runtime headers into outdir (compile_and_load already does this,
    # but we need the path for building the C harness)
    rt_dir = Path(__file__).parents[2] / "src" / "zuspec" / "be" / "rtl" / "rt"
    import shutil
    for hdr in rt_dir.glob("*.h"):
        dest = outdir / hdr.name
        if not dest.exists():
            shutil.copy(hdr, dest)

    so_path  = outdir / "PicoRV32.so"
    bin_path = outdir / "bench_zuspec"
    bench_c  = _BENCH / "bench_zuspec.c"

    subprocess.check_call([
        "cc", "-O2",
        "-o", str(bin_path),
        str(bench_c),
        f"-I{outdir}",
        str(so_path),
        f"-Wl,-rpath,{outdir}",
    ])

    return bin_path


# ── Shared fixture: build Verilator binary ────────────────────────────────────

@pytest.fixture(scope="module")
def verilator_bench_bin(tmp_path_factory, verilator_path):
    """Verilate picorv32.v with bench_verilator.cpp; return path to binary."""
    if not _PICORV32_V.exists():
        pytest.skip(f"picorv32.v not found at {_PICORV32_V}")

    outdir  = tmp_path_factory.mktemp("picorv32_verilator")
    obj_dir = outdir / "obj_dir"

    from .conftest import verilator_precompile
    binary = verilator_precompile(
        bench_cpp   = _BENCH / "bench_verilator.cpp",
        dut_sv      = _PICORV32_V,
        module_name = "picorv32",
        obj_dir     = obj_dir,
        tmp_dir     = outdir,
        verilator_bin = verilator_path,
    )
    return binary


# ── Benchmark: Zuspec C ───────────────────────────────────────────────────────

@pytest.mark.benchmark_test
def test_picorv32_zuspec(zuspec_bench_bin, benchmark):
    """PicoRV32 1M-loop: Zuspec-compiled C throughput."""
    def _run():
        subprocess.check_call(
            [str(zuspec_bench_bin)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    # 16M iterations × ~12 cycles/iteration ≈ 192M cycles
    approx_cycles = 192_000_016
    benchmark.extra_info.update(
        approx_Mcycles=approx_cycles / 1e6,
        approx_MHz=approx_cycles / mean_s / 1e6,
        component="PicoRV32",
        simulator="zuspec-compiled-C",
    )


# ── Benchmark: Verilator ──────────────────────────────────────────────────────

@pytest.mark.benchmark_test
def test_picorv32_verilator(verilator_bench_bin, benchmark):
    """PicoRV32 1M-loop: Verilator throughput."""
    def _run():
        subprocess.check_call(
            [str(verilator_bench_bin)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    benchmark(_run)
    mean_s = benchmark.stats.get("mean", 1.0)
    approx_cycles = 192_000_016
    benchmark.extra_info.update(
        approx_Mcycles=approx_cycles / 1e6,
        approx_MHz=approx_cycles / mean_s / 1e6,
        component="PicoRV32",
        simulator="verilator",
    )


# ── Quick functional smoke (always runs, no --run-benchmarks flag) ────────────

def test_picorv32_zuspec_functional(zuspec_bench_bin):
    """Verify bench_zuspec exits 0 and produces correct result."""
    out = subprocess.run(
        [str(zuspec_bench_bin)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, f"bench_zuspec failed:\n{out.stderr}"
    assert "result=16000000" in out.stdout, f"Wrong result:\n{out.stdout}"


def test_picorv32_verilator_functional(verilator_bench_bin):
    """Verify Verilator bench exits 0 and produces correct result."""
    out = subprocess.run(
        [str(verilator_bench_bin)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, f"Verilator bench failed:\n{out.stderr}"
    assert "result=16000000" in out.stdout, f"Wrong result:\n{out.stdout}"

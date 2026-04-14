"""
Benchmark test conftest.py.

Tests are skipped by default; pass ``--run-benchmarks`` to enable them.
Detects iverilog and verilator in PATH and exposes them as fixtures.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import pytest

# ---- Custom CLI option ---------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--run-benchmarks",
        action="store_true",
        default=False,
        help="Run benchmark tests (skipped by default).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "benchmark_test: performance benchmark (requires --run-benchmarks)",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-benchmarks", default=False):
        skip = pytest.mark.skip(reason="pass --run-benchmarks to run")
        for item in items:
            if "benchmark_test" in item.keywords:
                item.add_marker(skip)


# ---- Simulator detection -------------------------------------------------

def _find_sim(name: str) -> Optional[str]:
    return shutil.which(name)


IVERILOG  = _find_sim("iverilog")
VERILATOR = _find_sim("verilator")


@pytest.fixture(scope="session")
def iverilog_path():
    if IVERILOG is None:
        pytest.skip("iverilog not found in PATH")
    return IVERILOG


@pytest.fixture(scope="session")
def verilator_path():
    if VERILATOR is None:
        pytest.skip("verilator not found in PATH")
    return VERILATOR


# ---- Wall-clock timing helper -------------------------------------------

class SimTimer:
    """Simple wall-clock timer around a subprocess call."""

    def __init__(self, cmd, *, cwd=None):
        self._cmd = cmd
        self._cwd = cwd
        self.elapsed: float = 0.0

    def run(self):
        t0 = time.perf_counter()
        subprocess.check_call(
            self._cmd,
            cwd=self._cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.elapsed = time.perf_counter() - t0
        return self.elapsed


# ---- iverilog bench helper -----------------------------------------------

def iverilog_bench_cycles(
    tb_sv: Path,
    dut_sv: Path,
    n_cycles: int,
    tmp_dir: Path,
    iverilog_bin: str,
) -> float:
    """Compile + run an iverilog benchmark; return wall-clock seconds."""
    out_vvp = tmp_dir / "bench.vvp"
    subprocess.check_call(
        [iverilog_bin, "-g2012", "-o", str(out_vvp), str(dut_sv), str(tb_sv)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    t = SimTimer(
        ["vvp", str(out_vvp), f"+CYCLES={n_cycles}"],
        cwd=str(tmp_dir),
    )
    return t.run()


# ---- Verilator bench helper ----------------------------------------------

def verilator_bench_cycles(
    bench_cpp: Path,
    dut_sv: Path,
    module_name: str,
    n_cycles: int,
    tmp_dir: Path,
    verilator_bin: str,
) -> float:
    """Compile + run a Verilator benchmark (C++ harness); return wall-clock seconds."""
    obj_dir = tmp_dir / "obj_dir"
    subprocess.check_call(
        [
            verilator_bin,
            "--cc", "--exe", "--build",
            "-O2",
            "--top-module", module_name,
            "--Mdir", str(obj_dir),
            str(dut_sv), str(bench_cpp),
            "--CFLAGS", "-O2",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(tmp_dir),
    )
    binary = obj_dir / f"V{module_name}"
    t = SimTimer([str(binary), f"+CYCLES={n_cycles}"])
    return t.run()


def verilator_precompile(
    bench_cpp: Path,
    dut_sv: Path,
    module_name: str,
    obj_dir: Path,
    tmp_dir: Path,
    verilator_bin: str,
    extra_args: Optional[List[str]] = None,
) -> Path:
    """Compile Verilator model; return path to binary (for run-only benchmarks)."""
    cmd = [
        verilator_bin,
        "--cc", "--exe", "--build",
        "-O2",
        "--top-module", module_name,
        "--Mdir", str(obj_dir),
        str(dut_sv), str(bench_cpp),
        "--CFLAGS", "-O2",
    ]
    if extra_args:
        cmd.extend(extra_args)
    subprocess.check_call(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(tmp_dir),
    )
    return obj_dir / f"V{module_name}"

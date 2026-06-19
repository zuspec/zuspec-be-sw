"""Harness for the PSS → C → SV/DPI bridge e2e tests (B1).

Builds the generated scenario + zsp_bridge runtime (+ dv-solve when needed) into
``libzsp_scenario.so``, generates the SV shim, compiles a Verilator sim that
links the ``.so``, runs it, and returns stdout. Skips cleanly when the toolchain
(gcc / Verilator) or the solver is unavailable.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

import pytest

_SW = Path(__file__).resolve().parents[2] / "src" / "zuspec" / "be" / "sw"
_SHARE = _SW / "share"
_CBRIDGE = _SW / "scenario" / "cbridge"

_RT = [
    "zsp_alloc", "zsp_timebase", "zsp_thread", "zsp_list", "zsp_object",
    "zsp_component", "zsp_struct", "zsp_map", "zsp_fifo", "zsp_mutex",
    "zsp_indexed_pool", "zsp_par_block", "zsp_select", "zsp_memory",
    "zsp_channel",
]


def _verilator() -> str | None:
    for c in ("verilator", "verilator_bin"):
        p = shutil.which(c)
        if p:
            return p
    # fall back to the in-repo binary
    cand = (Path(__file__).resolve().parents[4] / "verilator-bin" / "bin"
            / "verilator")
    return str(cand) if cand.exists() else None


def _dv_solve_root() -> Path | None:
    for p in Path(__file__).resolve().parents:
        for c in (p / "dv-solve", p / "packages" / "dv-solve"):
            if (c / "src" / "c" / "zsp_problem.h").exists():
                return c
    return None


def require_sv_toolchain(needs_solver: bool = False):
    pytest.importorskip("zuspec.fe.pss")
    if not shutil.which("gcc"):
        pytest.skip("no gcc")
    if _verilator() is None:
        pytest.skip("no verilator")
    if needs_solver:
        root = _dv_solve_root()
        if root is None or not list((root / "build").glob("libdv_solve.so*")):
            pytest.skip("dv-solve not built (packages/dv-solve/build)")


def run_pss_over_sv(tmp_path: Path, pss_text: str, root: str = "pss_top",
                    exports=None, needs_solver: bool = False,
                    custom_tb: str = None) -> Tuple[str, int]:
    require_sv_toolchain(needs_solver=needs_solver)
    from _pss_harness import lower_pss
    from zuspec.be.sw.scenario.driver import generate_c_bridge
    from zuspec.be.sw.scenario.sv_shim import generate_sv_shim

    from zuspec.be.sw.scenario import build_dpi_library

    module, ctx = lower_pss(pss_text, root=root, exports=exports)
    gen = tmp_path / "gen"
    sources, ids = generate_c_bridge(module, ctx, gen)

    # --- build libzsp_scenario.so via the production API ---
    result, so, _ = build_dpi_library(sources, gen)
    if not result.success:
        pytest.fail("scenario .so build failed:\n" + result.stderr)
    dvs = _dv_solve_root()

    # --- SV shim + Verilator sim linking the .so ---
    sv = generate_sv_shim(ids, gen, imports=module.imports,
                          with_tb=(custom_tb is None))
    sv_files = [str(sv)]
    if custom_tb is not None:
        tb = gen / "tb.sv"
        tb.write_text(custom_tb)
        sv_files.append(str(tb))
    # --export-dynamic: the scenario .so calls back into SV `export "DPI-C"`
    # functions (synchronous solve imports); those symbols live in the verilated
    # executable and must be in its dynamic symbol table for the .so to resolve.
    ld = f"-Wl,--export-dynamic -L{gen} -lzsp_scenario -Wl,-rpath,{gen}"
    if needs_solver and dvs is not None:
        ld += f" -L{dvs / 'build'} -ldv_solve -Wl,-rpath,{dvs / 'build'}"
    vcmd = [_verilator(), "--binary", "--timing", "-j", "4", "-Wno-fatal",
            "--top-module", "tb"] + sv_files + [
            "-CFLAGS", f"-I{gen}", "-LDFLAGS", ld, "-o", "sim"]
    r = subprocess.run(vcmd, capture_output=True, text=True, cwd=str(gen),
                       timeout=300)
    if r.returncode != 0:
        pytest.fail("verilator build failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])

    exe = gen / "obj_dir" / "sim"
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    return run.stdout, run.returncode

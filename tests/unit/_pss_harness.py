"""Shared harness for PSS → C end-to-end tests (impl-plan §4).

``pss_c_case(pss_text, root, seed, iters)`` returns ``(stdout, rc)`` for a
compiled-and-run scenario, or raises ``pytest.skip`` when the toolchain / solver
is unavailable.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Tuple

import pytest

_HAS_CC = any(shutil.which(c) for c in ("gcc", "clang", "cc"))


def require_toolchain(needs_solver: bool = False):
    pytest.importorskip("zuspec.fe.pss")
    if not _HAS_CC:
        pytest.skip("no C compiler available")
    if needs_solver:
        from zuspec.be.sw.scenario import find_solver_paths
        if find_solver_paths() is None:
            pytest.skip("dv-solve library not found (set ZSP_SOLVER_PATH or "
                        "build packages/dv-solve)")


def pss_c_case(tmp_path: Path, pss_text: str, root: str = "pss_top",
               seed: int = 1, iters: int = 1,
               needs_solver: bool = False) -> Tuple[str, int]:
    require_toolchain(needs_solver=needs_solver)
    from zuspec.be.sw.scenario import generate_c_files, build_executable

    src = tmp_path / "case.pss"
    src.write_text(pss_text)
    out = tmp_path / "gen"
    sources = generate_c_files([src], out, root=root)

    exe = out / "case"
    result, _ = build_executable(sources, exe, out)
    if not result.success:
        pytest.fail("compile failed:\n" + result.stderr)

    # Uniform CLI: argv = (seed, iters).
    run = subprocess.run([str(exe), str(seed), str(iters)],
                         capture_output=True, text=True, timeout=30)
    return run.stdout, run.returncode


def lower_pss(pss_text: str, root: str = "pss_top", exports=None):
    """Parse + lower PSS to a (module, ctx) pair for IR injection tests."""
    from zuspec.fe.pss import Parser
    from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
    from zuspec.ir.core.xf import PSSToScenarioPass
    p = Parser()
    p.parses([("inj.pss", pss_text)])
    ctx = AstToIrTranslator().translate(p.link(), annotations=p.annotations)
    assert not ctx.errors, ctx.errors
    module = PSSToScenarioPass(root=root, exports=exports).lower(ctx)
    return module, ctx


def build_run_module(tmp_path: Path, module, ctx, seed: int = 1,
                     iters: int = 1) -> Tuple[str, int]:
    """Emit + compile + run an already-lowered (possibly injected) module."""
    from zuspec.be.sw.scenario import generate_c, build_executable
    out = tmp_path / "gen"
    sources = generate_c(module, ctx, out)
    exe = out / "case"
    result, _ = build_executable(sources, exe, out)
    if not result.success:
        pytest.fail("compile failed:\n" + result.stderr)
    run = subprocess.run([str(exe), str(seed), str(iters)],
                         capture_output=True, text=True, timeout=30)
    return run.stdout, run.returncode


def msg_stmt(text: str):
    """Build a Layer-0 ``self.message(NONE, "text")`` statement for injection."""
    import zuspec.ir.core as ir
    return ir.StmtExpr(expr=ir.ExprCall(
        func=ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr="message"),
        args=[ir.ExprConstant(value=0), ir.ExprConstant(value=text)]))

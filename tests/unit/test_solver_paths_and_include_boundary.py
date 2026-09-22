"""dv-solve discovery, and the solver/backend include boundary.

Two things are under test here and they are related:

  * ``solver_paths.find_solver_paths()`` must find an INSTALLED dv-solve, not
    only a sibling checkout. It used to walk its ancestors for a
    ``packages/dv-solve`` directory, so a wheel install -- libraries, headers
    and all -- reported "not found" and every solver-using scenario skipped.

  * ``driver.build_executable()`` / ``build_dpi_library()`` must compile the
    solver translation unit against dv-solve's headers and the backend TUs
    against be-sw's, never both together. The two projects ship a colliding
    ``zsp_alloc.h`` (``free(self, ptr)`` vs ``release(self, ptr, size)``).

The include-boundary tests deliberately make each TU *use* a field that only
its own ``zsp_alloc.h`` declares, so picking up the wrong header is a compile
error rather than a silent struct-layout mismatch. That is the only way to
test this: with the headers as they stand the wrong choice is currently
invisible, because the generated solver TU never includes ``zsp_alloc.h``
directly and GCC's quoted-include rule prefers a header's own directory when
one dv-solve header pulls in another. Both of those are accidents that a
one-line change elsewhere would remove.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from zuspec.be.sw.scenario import solver_paths as sp
from zuspec.be.sw.scenario.driver import (
    build_dpi_library, build_executable, _partition_sources)

pytestmark = pytest.mark.skipif(shutil.which("gcc") is None,
                                reason="gcc not available")


@pytest.fixture
def solver():
    paths = sp.find_solver_paths()
    if paths is None:
        pytest.skip("dv-solve not available on this host")
    return paths


# --------------------------------------------------------------- discovery --


def test_finds_an_installed_package(monkeypatch):
    """The regression: discovery must not require a checkout.

    The sibling-checkout walk is disabled so that only the package path can
    answer -- otherwise this passes in a monorepo for the wrong reason.
    """
    pytest.importorskip("dv_solve")
    monkeypatch.delenv("ZSP_SOLVER_PATH", raising=False)
    monkeypatch.setattr(sp, "_find_dv_solve_root", lambda: None)
    found = sp.find_solver_paths()
    if found is None:
        pytest.skip("dv-solve package has no built libraries here")
    assert (found.lib_dir / "libdv_solve.so").exists()


def test_include_dirs_is_plural_and_usable(solver):
    """``get_incdirs()`` reports two directories for an installed layout; a
    single ``include_dir`` could not express that, and the nested one is the
    only place unqualified ``#include "zsp_ctx.h"`` resolves."""
    assert len(solver.include_dirs) >= 1
    assert any((Path(d) / "zsp_problem.h").is_file()
               for d in solver.include_dirs)


def test_include_dir_stays_backwards_compatible(solver):
    """``SolverPaths.include_dir`` is public API (re-exported from
    ``scenario/__init__``); existing callers must keep working."""
    assert solver.include_dir == solver.include_dirs[0]


def test_env_override_wins(tmp_path, monkeypatch):
    """A complete fake install under ZSP_SOLVER_PATH is chosen over anything
    else discovery could find."""
    prefix = tmp_path / "prefix"
    (prefix / "lib").mkdir(parents=True)
    (prefix / "include").mkdir(parents=True)
    (prefix / "lib" / "libdv_solve.so").write_bytes(b"")
    (prefix / "include" / "zsp_problem.h").write_text("")
    monkeypatch.setenv("ZSP_SOLVER_PATH", str(prefix))
    found = sp.find_solver_paths()
    assert found.lib_dir == prefix / "lib"
    # The base prefix rides along (harmlessly, and deliberately: dv-solve's own
    # get_incdirs() reports a base plus a nested dir the same way). What the
    # contract requires is that a directory actually holding the headers is in
    # the set.
    assert prefix / "include" in found.include_dirs


def test_returns_none_when_nothing_is_available(monkeypatch):
    """Callers rely on ``None`` to skip with a reason. Returning a plausible
    but unpopulated directory instead turns that into ``cannot find
    -ldv_solve`` at the end of a long build."""
    monkeypatch.delenv("ZSP_SOLVER_PATH", raising=False)
    monkeypatch.setattr(sp, "_from_package", lambda: None)
    monkeypatch.setattr(sp, "_find_dv_solve_root", lambda: None)
    assert sp.find_solver_paths() is None


def test_unbuilt_package_is_not_reported_as_found(monkeypatch, tmp_path):
    """``dv_solve.get_libdirs()`` names the package directory even when
    nothing is built there, so its answer has to be verified, not trusted."""
    dv = pytest.importorskip("dv_solve")
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.delenv("ZSP_SOLVER_PATH", raising=False)
    monkeypatch.setattr(dv, "get_libdirs", lambda: [str(empty)])
    assert sp._from_package() is None


def test_diagnostic_names_the_fixes():
    msg = sp.solver_not_found_message()
    assert "ZSP_SOLVER_PATH" in msg and "pip install dv-solve" in msg


# ------------------------------------------------------- the two-TU fixture --

#: A header both sides include. Kept free of either runtime's headers, exactly
#: as the emitter keeps the generated scenario header free of them.
_SHARED_H = """
#ifndef SCENARIO_GEN_H
#define SCENARIO_GEN_H
#include <stdint.h>
extern int32_t g_x;
void scenario_solve_all(void);
#endif
"""

#: The BACKEND TU. Uses ``zsp_alloc_t::free``, which only be-sw's
#: ``zsp_alloc.h`` declares -- so if dv-solve's headers leaked into this TU's
#: include path ahead of be-sw's, this fails to compile.
_BACKEND_C = """
#include "scenario_gen.h"
#include "zsp_alloc.h"
#include <stdio.h>
int32_t g_x = -1;
static int uses_be_sw_alloc(void) {
    zsp_alloc_t a;
    zsp_alloc_malloc_init(&a);
    return a.free != 0;          /* be-sw spelling; dv-solve calls it release */
}
int main(void) {
    if (!uses_be_sw_alloc()) return 2;
    scenario_solve_all();
    printf("x=%d\\n", (int)g_x);
    return 0;
}
"""


def _solver_c(problem_bytes):
    """The SOLVER TU. Uses ``ZSP_ALLOC``, a macro only dv-solve's
    ``zsp_alloc.h`` defines, so a leak in the other direction also fails to
    compile. Solves a real embedded problem and publishes the result."""
    data = ",".join(str(b) for b in problem_bytes)
    return """
#include "scenario_gen.h"
#include "zsp_problem.h"
#include "zsp_block_alloc.h"
#include "zsp_alloc.h"
#include "zsp_ctx.h"
#include "zsp_search.h"
#include <string.h>

static const unsigned char prob[] = {%s};

/* Only dv-solve's zsp_alloc.h has a 'release' member; be-sw's calls it
   'free' and gives it a different signature. Referencing it is a
   compile-time assertion that this TU got the right header -- and needs no
   symbol from the library, so it stays a pure include-path test. */
static int uses_dv_solve_alloc(void) {
    zsp_alloc_t a;
    memset(&a, 0, sizeof(a));
    return a.release == 0;
}

/* The driver decides a scenario needs the solver by looking for the text
   solve_problem_init( in the emitted source. Mentioning it here exercises
   that detection without calling it. */
void scenario_solve_all(void) {
    static unsigned char cbuf[1<<20];
    if (!uses_dv_solve_alloc()) { g_x = -2; return; }
    zsp_block_alloc_t *ba = zsp_block_alloc_create(0, 1<<20);
    SolveCtx *c = solver_create(cbuf, sizeof(cbuf), ba);
    solver_compile(c, (SolveProblem *)prob);
    SolveOpts o; memset(&o, 0, sizeof(o));
    o.seed = 12345ull; o.fair_pick = 1;
    solver_solve(c, &o);
    g_x = (int32_t)solver_get_value(c, 0);
    solver_destroy(c);
    zsp_block_alloc_destroy(ba);
}
""" % data


def _build_problem():
    """A real constrained problem: one 8-bit var with 200 < x < 210."""
    dv = pytest.importorskip("dv_solve")
    from dv_solve.builder import SolveProblemBuilder
    from dv_solve.problem import BIN_GT, BIN_LT

    b = SolveProblemBuilder()
    b.add_var(0, width=8, is_signed=False, lo=0, hi=255)
    b.add_constraint(b.expr_binary(BIN_GT, b.expr_var(0), b.expr_const(200, 8)))
    b.add_constraint(b.expr_binary(BIN_LT, b.expr_var(0), b.expr_const(210, 8)))
    return b.finalize_bytes()


@pytest.fixture
def scenario(tmp_path):
    """Write the three files the two entry points consume."""
    (tmp_path / "scenario_gen.h").write_text(_SHARED_H)
    backend = tmp_path / "scenario_gen.c"
    backend.write_text(_BACKEND_C)
    solve = tmp_path / "scenario_solve.c"
    solve.write_text(_solver_c(_build_problem()))
    return tmp_path, [backend, solve]


# ------------------------------------------------------------- partitioning --


def test_partition_identifies_the_solver_tu(scenario):
    _out, (backend, solve) = scenario
    backend_tus, solver_tus = _partition_sources([backend, solve])
    assert backend_tus == [backend]
    assert solver_tus == [solve]


def test_partition_is_by_content_not_by_name(tmp_path):
    """Renaming what the emitter writes must not silently put a solver TU back
    into the backend's include set."""
    odd = tmp_path / "not_obviously_a_solver_file.c"
    odd.write_text('#include "zsp_problem.h"\n')
    backend_tus, solver_tus = _partition_sources([odd])
    assert solver_tus == [odd] and backend_tus == []


# --------------------------------------------------- build_executable, real --


def test_build_executable_compiles_links_and_solves(scenario, solver):
    """The end-to-end claim: both include sets applied to the right TUs, the
    solver library linked, and a real solve at run time."""
    out, sources = scenario
    exe = out / "scenario"
    result, paths = build_executable(sources, exe, out, link_solver=True)
    assert result.success, result.stderr
    assert paths is not None

    r = subprocess.run([str(exe)], capture_output=True, text=True, cwd=str(out))
    assert r.returncode == 0, r.stderr
    value = int(r.stdout.strip().split("=")[1])
    assert 200 < value < 210, "solver returned %d, outside the constraint" % value


def test_build_executable_detects_the_solver_automatically(scenario, solver):
    """``link_solver=None`` must infer the need from the emitted code."""
    out, sources = scenario
    result, paths = build_executable(sources, out / "auto", out)
    assert result.success, result.stderr
    assert paths is not None


def test_build_executable_without_a_solver_still_works(tmp_path):
    """Scenarios that do not need the solver must not regress -- and must not
    require dv-solve to be present at all."""
    src = tmp_path / "plain.c"
    src.write_text("#include <stdio.h>\nint main(void){puts(\"ok\");return 0;}\n")
    result, paths = build_executable([src], tmp_path / "plain", tmp_path)
    assert result.success, result.stderr
    assert paths is None
    r = subprocess.run([str(tmp_path / "plain")], capture_output=True, text=True)
    assert r.stdout.strip() == "ok"


def test_missing_solver_is_an_actionable_failure(scenario, monkeypatch):
    out, sources = scenario
    monkeypatch.setattr("zuspec.be.sw.scenario.driver.find_solver_paths",
                        lambda: None)
    result, paths = build_executable(sources, out / "x", out, link_solver=True)
    assert not result.success and paths is None
    assert "ZSP_SOLVER_PATH" in result.stderr


# -------------------------------------------------- build_dpi_library, real --


def test_build_dpi_library_keeps_the_include_sets_apart(scenario, solver):
    """The same boundary, through the other entry point.

    A shared library tolerates undefined symbols, so this asserts on the
    compile succeeding and the solver library actually being linked in --
    which is what the DPI consumer needs.
    """
    out, sources = scenario
    result, so, paths = build_dpi_library(sources, out, so_name="libscn.so",
                                          link_solver=True)
    assert result.success, result.stderr
    assert so.exists() and paths is not None

    if shutil.which("ldd"):
        deps = subprocess.run(["ldd", str(so)], capture_output=True, text=True)
        assert "libdv_solve" in deps.stdout


def test_build_dpi_library_without_a_solver(tmp_path):
    src = tmp_path / "plain.c"
    src.write_text("int zsp_noop(void){return 0;}\n")
    result, so, paths = build_dpi_library([src], tmp_path,
                                          so_name="libplain.so",
                                          link_solver=False)
    assert result.success, result.stderr
    assert paths is None and so.exists()

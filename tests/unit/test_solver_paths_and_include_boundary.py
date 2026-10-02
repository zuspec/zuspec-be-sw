"""dv-solve discovery, and the solver/backend include boundary.

Two things are under test here and they are related:

  * ``solver_paths.find_solver_paths()`` must find an INSTALLED dv-solve, not
    only a sibling checkout. It used to walk its ancestors for a
    ``packages/dv-solve`` directory, so a wheel install -- libraries, headers
    and all -- reported "not found" and every solver-using scenario skipped.

  * ``driver.build_executable()`` / ``build_dpi_library()`` must compile the
    solver translation unit against dv-solve's headers and the backend TUs
    against be-sw's, never both together. The two projects used to ship a
    colliding ``zsp_alloc.h``; dv-solve's names are now ``dvs_``-prefixed
    behind one public header, ``dv_solve.h``, but each TU should still see
    only its own project's headers.

The include-boundary tests make each TU prove which include set it got: the
backend TU uses a field only be-sw's ``zsp_alloc.h`` declares, and the solver
TU checks that ``dv_solve.h`` is reachable and be-sw's ``zsp_alloc.h`` is not.
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
    only place unqualified ``#include "dv_solve.h"`` resolves."""
    assert len(solver.include_dirs) >= 1
    assert any((Path(d) / "dv_solve.h").is_file()
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
    (prefix / "include" / "dv_solve.h").write_text("")
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
    monkeypatch.setattr(sp, "_dv_solve_resolver", lambda: None)
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
    monkeypatch.setattr(sp, "_dv_solve_resolver", lambda: None)  # older API
    monkeypatch.setattr(dv, "get_libdirs", lambda: [str(empty)])
    assert sp._from_package() is None


# ----------------------------------- linkability and installation selection --
#
# Each case runs twice: delegated to dv-solve's installation API, and through
# this module's standalone rules (dv-solve absent or older). The two must
# agree -- that is what "one contract" means.


@pytest.fixture(params=["delegated", "standalone"])
def mode(request, monkeypatch):
    monkeypatch.delenv("ZSP_SOLVER_PATH", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    if request.param == "delegated":
        if sp._dv_solve_resolver() is None:
            pytest.skip("dv-solve with the installation API is not importable "
                        "(an older dv_solve is shadowing it?)")
    else:
        monkeypatch.setattr(sp, "_dv_solve_resolver", lambda: None)
        monkeypatch.setattr(sp, "_from_package", lambda: None)
    return request.param


def _prefix(tmp_path, lib=None):
    """A prefix with headers and, optionally, one library entry built by *lib*."""
    prefix = tmp_path / "prefix"
    (prefix / "lib").mkdir(parents=True)
    (prefix / "include").mkdir()
    (prefix / "include" / "dv_solve.h").write_text("")
    if lib is not None:
        lib(prefix / "lib")
    return prefix


def test_versioned_only_override_is_not_usable(tmp_path, monkeypatch, mode):
    """``-ldv_solve`` cannot resolve ``libdv_solve.so.1``. Reported as the
    override's problem -- not replaced by the package or a checkout."""
    prefix = _prefix(tmp_path,
                     lambda d: (d / "libdv_solve.so.1").write_bytes(b""))
    monkeypatch.setenv("ZSP_SOLVER_PATH", str(prefix))
    with pytest.raises(sp.SolverDiscoveryError) as ei:
        sp.find_solver_paths()
    assert "ZSP_SOLVER_PATH=%s" % prefix in str(ei.value)
    assert "libdv_solve.so.1" in str(ei.value)


def test_directory_named_like_the_library_is_not_usable(
        tmp_path, monkeypatch, mode):
    prefix = _prefix(tmp_path, lambda d: (d / "libdv_solve.so").mkdir())
    monkeypatch.setenv("ZSP_SOLVER_PATH", str(prefix))
    with pytest.raises(sp.SolverDiscoveryError, match="ZSP_SOLVER_PATH"):
        sp.find_solver_paths()


def test_dangling_symlink_is_not_usable(tmp_path, monkeypatch, mode):
    prefix = _prefix(tmp_path, lambda d: os.symlink(
        str(d / "gone.so.1"), str(d / "libdv_solve.so")))
    monkeypatch.setenv("ZSP_SOLVER_PATH", str(prefix))
    with pytest.raises(sp.SolverDiscoveryError, match="ZSP_SOLVER_PATH"):
        sp.find_solver_paths()


def test_valid_unversioned_symlink_is_usable(tmp_path, monkeypatch, mode):
    """The ordinary shape of an installed library: linker name -> soname."""
    def lib(d):
        (d / "libdv_solve.so.1").write_bytes(b"")
        os.symlink("libdv_solve.so.1", str(d / "libdv_solve.so"))
    prefix = _prefix(tmp_path, lib)
    monkeypatch.setenv("ZSP_SOLVER_PATH", str(prefix))
    found = sp.find_solver_paths()
    assert found.lib_dir == prefix / "lib"


def test_override_without_headers_is_not_completed_elsewhere(
        tmp_path, monkeypatch, mode):
    lib_only = tmp_path / "lib_only"
    lib_only.mkdir()
    (lib_only / "libdv_solve.so").write_bytes(b"")
    monkeypatch.setenv("ZSP_SOLVER_PATH", str(lib_only))
    with pytest.raises(sp.SolverDiscoveryError, match="headers"):
        sp.find_solver_paths()


def test_checkout_build_selected_by_its_versioned_library(tmp_path, monkeypatch):
    """Standalone checkout rules match dv-solve's: ``build/`` holds only the
    soname, so it is selected and reported unlinkable -- ``_build/`` is not
    quietly linked instead."""
    monkeypatch.delenv("ZSP_SOLVER_PATH", raising=False)
    monkeypatch.setattr(sp, "_dv_solve_resolver", lambda: None)
    monkeypatch.setattr(sp, "_from_package", lambda: None)
    root = tmp_path / "dv-solve"
    (root / "src" / "c").mkdir(parents=True)
    (root / "src" / "c" / "dv_solve.h").write_text("")
    (root / "build" / "lib").mkdir(parents=True)
    (root / "build" / "lib" / "libdv_solve.so.1").write_bytes(b"")
    (root / "_build" / "lib").mkdir(parents=True)
    (root / "_build" / "lib" / "libdv_solve.so").write_bytes(b"")
    monkeypatch.setattr(sp, "_find_dv_solve_root", lambda: root)
    with pytest.raises(sp.SolverDiscoveryError, match="checkout build"):
        sp.find_solver_paths()


def test_delegated_failure_does_not_fall_back_to_a_checkout(
        tmp_path, monkeypatch):
    """dv-solve selects its package (versioned-only library). be-sw's own
    sibling-checkout search must not paper over that."""
    resolver = sp._dv_solve_resolver()
    if resolver is None:
        pytest.skip("dv-solve with the installation API is not importable")
    monkeypatch.delenv("ZSP_SOLVER_PATH", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    pkg = tmp_path / "site" / "dv_solve"
    pkg.mkdir(parents=True)
    (pkg / "libdv_solve.so.1").write_bytes(b"")
    monkeypatch.setattr(resolver, "_pkg_dir", lambda: str(pkg))
    monkeypatch.setattr(resolver, "_src_root", lambda: str(tmp_path / "none"))
    with pytest.raises(sp.SolverDiscoveryError, match="package installation"):
        sp.find_solver_paths()


def test_delegated_nothing_installed_is_none_not_a_checkout(
        tmp_path, monkeypatch):
    """With dv-solve importable, "nothing installed" is its answer; a sibling
    checkout would be a different installation from the one Python runs."""
    resolver = sp._dv_solve_resolver()
    if resolver is None:
        pytest.skip("dv-solve with the installation API is not importable")
    monkeypatch.delenv("ZSP_SOLVER_PATH", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    monkeypatch.setattr(resolver, "_pkg_dir", lambda: str(tmp_path / "pkg"))
    monkeypatch.setattr(resolver, "_src_root", lambda: str(tmp_path / "none"))
    assert sp.find_solver_paths() is None


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
    """The SOLVER TU. Compiles against dv-solve's public header and fails to
    compile if be-sw's ``zsp_alloc.h`` is on its include path, so a leak in
    the other direction is caught too. Solves a real embedded problem and
    publishes the result."""
    data = ",".join(str(b) for b in problem_bytes)
    return """
#include "scenario_gen.h"
#include "dv_solve.h"
#include <string.h>

#if defined(__has_include)
#if __has_include("zsp_alloc.h")
#error "be-sw's runtime headers leaked into the solver TU's include path"
#endif
#endif

static const unsigned char prob[] = {%s};

/* The driver decides a scenario needs the solver by looking for the text
   dvs_builder_create( in the emitted source. Mentioning it here exercises
   that detection without calling it. */
void scenario_solve_all(void) {
    static unsigned char cbuf[1<<20];
    dvs_block_alloc_t *ba = dvs_block_alloc_create(0, 1<<20);
    dvs_ctx_t *c = dvs_solver_create(cbuf, sizeof(cbuf), ba);
    dvs_solver_compile(c, (dvs_problem_t *)prob);
    dvs_solve_opts_t o; memset(&o, 0, sizeof(o));
    o.seed = 12345ull; o.fair_pick = 1;
    if (dvs_solver_solve(c, &o) == DVS_SOLVE_OK)
        g_x = (int32_t)dvs_solver_get_value(c, 0);
    dvs_solver_destroy(c);
    dvs_block_alloc_destroy(ba);
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
    odd.write_text('#include "dv_solve.h"\n')
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


def test_unusable_installation_fails_the_build_naming_it(
        scenario, tmp_path, monkeypatch):
    """Both entry points surface the selected installation's problem rather
    than linking something else or reporting a generic "not found"."""
    out, sources = scenario
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "libdv_solve.so.1").write_bytes(b"")
    (bad / "dv_solve.h").write_text("")
    monkeypatch.setenv("ZSP_SOLVER_PATH", str(bad))
    result, paths = build_executable(sources, out / "x", out, link_solver=True)
    assert not result.success and paths is None
    assert "ZSP_SOLVER_PATH=%s" % bad in result.stderr
    result, so, paths = build_dpi_library(sources, out, link_solver=True)
    assert not result.success and paths is None
    assert "ZSP_SOLVER_PATH=%s" % bad in result.stderr


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


@pytest.mark.skipif(shutil.which("nm") is None or not sys.platform.startswith("linux"),
                    reason="needs nm and ELF dynamic symbols")
def test_build_dpi_library_loads_and_solves(scenario, solver):
    """Dependency inspection is not an executed solve: load the library and
    call it.

    Outside a simulator nothing provides the DPI imports (``svGetScope``,
    ``svSetScope``) or the SV-side exports the bridge calls back into, so
    exactly those -- whatever the library imports that neither dv-solve nor
    libc provides -- are stubbed in a library loaded ``RTLD_GLOBAL`` first.
    The solve itself is the real one, and the dv-solve library the process
    maps must be the one discovery named.
    """
    import ctypes
    out, sources = scenario
    result, so, paths = build_dpi_library(sources, out, so_name="libscn2.so",
                                          link_solver=True)
    assert result.success, result.stderr

    core = paths.lib_dir / "libdv_solve.so"
    defined = set(subprocess.run(["nm", "-D", "--defined-only", str(core)],
                                 capture_output=True, text=True).stdout.split())
    undef = [l.split()[-1] for l in subprocess.run(
        ["nm", "-uD", str(so)], capture_output=True, text=True).stdout.splitlines()
        if l.split()[0] == "U"]
    stubs = sorted(u for u in undef if "@" not in u and u not in defined)
    assert all(n.startswith(("sv", "zsp_")) for n in stubs), stubs
    stub_c = out / "sim_stubs.c"
    stub_c.write_text("".join("void *%s(void){return 0;}\n" % n for n in stubs))
    subprocess.run(["gcc", "-shared", "-fPIC", "-o", str(out / "libsimstub.so"),
                    str(stub_c)], check=True)
    ctypes.CDLL(str(out / "libsimstub.so"), mode=ctypes.RTLD_GLOBAL)

    lib = ctypes.CDLL(str(so))
    lib.scenario_solve_all.restype = None
    lib.scenario_solve_all()
    value = ctypes.c_int32.in_dll(lib, "g_x").value
    assert 200 < value < 210, "solver returned %d, outside the constraint" % value

    with open("/proc/self/maps") as f:
        mapped = {l.split()[-1] for l in f if "/libdv_solve." in l}
    assert {os.path.realpath(m) for m in mapped} == {os.path.realpath(str(core))}


def test_build_dpi_library_without_a_solver(tmp_path):
    src = tmp_path / "plain.c"
    src.write_text("int zsp_noop(void){return 0;}\n")
    result, so, paths = build_dpi_library([src], tmp_path,
                                          so_name="libplain.so",
                                          link_solver=False)
    assert result.success, result.stderr
    assert paths is None and so.exists()

"""Locate the dv-solve shared library + headers for linking generated C.

Discovery is DELEGATED to the installed ``dv_solve`` package's public API
(``get_libdirs`` / ``get_incdirs``), which is the single place that knows how
dv-solve lays itself out. This module used to walk its own ancestors looking
for a sibling ``packages/dv-solve`` checkout and probe that checkout's build
directories directly. That worked in a monorepo and nowhere else: with
dv-solve installed as a wheel there is no checkout to find, so a perfectly
good installation sitting in site-packages -- libraries, headers and all --
was reported as "not found", and every solver-using scenario skipped.

The order of precedence:

  1. ``ZSP_SOLVER_PATH``, handled here so the override still works when
     ``dv_solve`` is not importable at all, and honoured a second time inside
     dv-solve's own resolver when it is.
  2. The installed ``dv_solve`` package's public API.
  3. A sibling ``packages/dv-solve`` checkout -- the historical behaviour,
     kept as a fallback for a working tree where dv-solve has been built but
     not installed.

Returns ``None`` when nothing usable is found, so callers can skip with a
reason rather than emit a compile command that fails obscurely later.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence

#: A header present in every dv-solve include tree, used to tell a real
#: include directory from one that merely exists. An unbuilt checkout has a
#: ``src/c`` full of sources and a wheel with unstaged data files has an empty
#: ``share/include``; both look fine until a consumer's compile fails.
_SENTINEL_HEADER = "zsp_problem.h"


class SolverPaths(NamedTuple):
    """Where the solver's artifacts are, for a compile/link command.

    ``include_dirs`` is a SEQUENCE because the installed layout needs two
    entries: dv-solve stages its headers under ``share/include/dv_solve/``,
    but its own headers and the generated solver code both use unqualified
    includes (``#include "zsp_ctx.h"``), which resolve only against the nested
    directory -- while a consumer writing ``dv_solve/zsp_ctx.h`` needs the
    base. A single directory could not express that.

    ``include_dir`` is retained as the first entry so existing callers keep
    working; it is the right answer for a source tree, where the headers are
    flat, and the wrong one for a wheel, so new code should use the plural.

    WHAT THESE ARE NOT: this is the include set for the SOLVER translation
    unit only. dv-solve and zuspec-be-sw both ship a ``zsp_alloc.h`` declaring
    an incompatible ``struct zsp_alloc_s`` (``free`` vs ``release``, with
    different signatures), so the two sets must never be merged into one
    ``-I`` list -- see ``driver.py``.
    """
    lib_dir: Path
    include_dirs: Sequence[Path]
    lib_name: str = "dv_solve"

    @property
    def include_dir(self) -> Path:
        """The first include directory (backwards-compatible accessor)."""
        return self.include_dirs[0]


def _usable_incdirs(dirs: Sequence[str]) -> Optional[List[Path]]:
    """Keep *dirs* only if one of them actually holds the solver headers."""
    paths = [Path(d) for d in dirs if os.path.isdir(d)]
    if any((p / _SENTINEL_HEADER).is_file() for p in paths):
        return paths
    return None


def _from_env() -> Optional[SolverPaths]:
    """``ZSP_SOLVER_PATH``: a directory or a CMake install prefix."""
    root = os.environ.get("ZSP_SOLVER_PATH")
    if not root:
        return None
    base = Path(root)
    lib_dir = None
    for cand in (base, base / "lib", base / "lib64"):
        if cand.is_dir() and sorted(cand.glob("libdv_solve.so*")):
            lib_dir = cand
            break
    if lib_dir is None:
        return None
    incs = _usable_incdirs([
        str(base), str(base / "include"), str(base / "include" / "dv_solve"),
        str(base / "share" / "include"),
        str(base / "share" / "include" / "dv_solve"),
    ])
    if incs is None:
        return None
    return SolverPaths(lib_dir=lib_dir, include_dirs=incs)


def _from_package() -> Optional[SolverPaths]:
    """Ask the installed dv_solve package where its own artifacts are."""
    try:
        import dv_solve
    except ImportError:
        return None

    try:
        lib_dirs = dv_solve.get_libdirs()
        inc_dirs = dv_solve.get_incdirs()
    except Exception:
        return None

    # get_libdirs() falls back to naming the package directory when nothing is
    # built, so its answer has to be verified rather than trusted: handing an
    # unpopulated -L to the linker turns a clean skip into
    # "cannot find -ldv_solve" at the end of a long build.
    for d in lib_dirs:
        if sorted(Path(d).glob("libdv_solve.so*")):
            incs = _usable_incdirs(inc_dirs)
            if incs is None:
                return None
            return SolverPaths(lib_dir=Path(d), include_dirs=incs)
    return None


def _find_dv_solve_root() -> Optional[Path]:
    """Walk up from this file to a ``packages/dv-solve`` checkout."""
    here = Path(__file__).resolve()
    for p in here.parents:
        for cand in (p / "dv-solve", p / "packages" / "dv-solve"):
            if (cand / "src" / "c" / _SENTINEL_HEADER).exists():
                return cand
    return None


def _from_checkout() -> Optional[SolverPaths]:
    """The historical sibling-checkout search, now a last resort."""
    root = _find_dv_solve_root()
    if root is None:
        return None
    include_dir = root / "src" / "c"
    for bd in ("build", "_build", "build_release", "cmake-build-release"):
        for sub in ("lib", "lib64", ""):
            d = (root / bd / sub) if sub else (root / bd)
            if not d.is_dir():
                continue
            if sorted(d.glob("libdv_solve.so*")):
                incs = _usable_incdirs([str(include_dir)])
                if incs is None:
                    return None
                return SolverPaths(lib_dir=d, include_dirs=incs)
    return None


def find_solver_paths() -> Optional[SolverPaths]:
    """Locate dv-solve, or ``None`` if it is unavailable here."""
    for source in (_from_env, _from_package, _from_checkout):
        found = source()
        if found is not None:
            return found
    return None


def solver_not_found_message() -> str:
    """One actionable diagnostic, so both build entry points say the same
    thing about the same failure."""
    try:
        import dv_solve
        where = "importable from %s" % os.path.dirname(dv_solve.__file__)
    except ImportError:
        where = "not importable"
    return (
        "dv-solve not found: the scenario needs the constraint solver but no "
        "usable installation was located (dv_solve is %s).\n"
        "Fixes:\n"
        "  - pip install dv-solve\n"
        "  - or build a checkout:  cmake -S . -B build -G Ninja "
        "-DCMAKE_INSTALL_PREFIX=build && ninja -C build install\n"
        "  - or set ZSP_SOLVER_PATH to the install prefix / library directory."
        % where)

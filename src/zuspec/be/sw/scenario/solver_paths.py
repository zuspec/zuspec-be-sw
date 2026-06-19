"""Locate the dv-solve shared library + headers for linking generated C.

Discovery order (impl-plan §1 / resolved decision 5 — shared library):
  1. ``ZSP_SOLVER_PATH`` (a dir containing ``libdv_solve.so`` and/or headers).
  2. The in-repo ``dv-solve`` checkout: ``build/`` for the lib, ``src/c`` for
     headers.
Returns ``None`` when nothing is found so callers can skip-with-reason.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple, Optional


class SolverPaths(NamedTuple):
    lib_dir: Path          # directory containing libdv_solve.so
    include_dir: Path      # directory containing zsp_problem.h ...
    lib_name: str = "dv_solve"


def _find_dv_solve_root() -> Optional[Path]:
    """Walk up from this file to a ``packages/dv-solve`` checkout."""
    here = Path(__file__).resolve()
    for p in here.parents:
        cand = p / "dv-solve"
        if (cand / "src" / "c" / "zsp_problem.h").exists():
            return cand
        cand = p / "packages" / "dv-solve"
        if (cand / "src" / "c" / "zsp_problem.h").exists():
            return cand
    return None


def find_solver_paths() -> Optional[SolverPaths]:
    # 1. Explicit env override.
    env = os.environ.get("ZSP_SOLVER_PATH")
    candidates = []
    if env:
        candidates.append(Path(env))

    root = _find_dv_solve_root()
    include_dir = None
    if root is not None:
        include_dir = root / "src" / "c"
        for bd in ("build", "_build", "build_release", "cmake-build-release"):
            candidates.append(root / bd)

    for d in candidates:
        if not d.exists():
            continue
        hits = sorted(d.glob("libdv_solve.so*"), key=lambda p: len(p.name))
        if hits:
            inc = include_dir
            # If env dir also holds headers, prefer it.
            if (d / "zsp_problem.h").exists():
                inc = d
            if inc is None or not (inc / "zsp_problem.h").exists():
                return None
            return SolverPaths(lib_dir=hits[0].parent, include_dir=inc)
    return None

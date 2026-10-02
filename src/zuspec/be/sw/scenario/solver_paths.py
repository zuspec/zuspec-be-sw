"""Locate the dv-solve shared library + headers for linking generated C.

THE CONTRACT (shared with ``dv_solve._resolve``, which is authoritative):
discovery selects one INSTALLATION, and the library and headers returned both
come from it. The installation is

  1. ``ZSP_SOLVER_PATH`` when set -- terminal: if it is unusable that is an
     error, never a cue to try the package or a checkout;
  2. otherwise the first candidate holding a loadable ``libdv_solve``
     (unversioned, or a numerically versioned soname).

Once selected, the installation must hold a LINKABLE library -- a real file
(or a symlink to one) named ``libdv_solve.so``, since the build commands use
``-ldv_solve`` -- and the solver headers. If it does not,
:class:`SolverDiscoveryError` is raised naming it. A versioned-only directory,
a directory named ``libdv_solve.so`` and a dangling symlink are never
reported as usable.

Where the answer comes from:

  * dv-solve importable with its installation API: delegated entirely. Its
    answer is final, including "nothing installed" -- a sibling checkout of
    dv-solve is NOT consulted then, because the Python solver would be
    running out of the imported package while generated C linked the
    checkout.
  * Otherwise (dv-solve not importable, or an older dv-solve without that
    API): the same rules applied here over ``ZSP_SOLVER_PATH``, the older
    package's ``get_libdirs()``/``get_incdirs()``, and a sibling
    ``packages/dv-solve`` checkout's build directories.

``find_solver_paths()`` returns ``None`` only when nothing is installed at
all, so callers can skip with a reason; a broken selected installation raises.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence

#: A header present in every dv-solve include tree, used to tell a real
#: include directory from one that merely exists. An unbuilt checkout has a
#: ``src/c`` full of sources and a wheel with unstaged data files has an empty
#: ``share/include``; both look fine until a consumer's compile fails.
_SENTINEL_HEADER = "dv_solve.h"

#: The linker name ``-ldv_solve`` resolves, and the loadable soname forms.
_LINK_NAME = "libdv_solve.so"
_VERSIONED = re.compile(r"^libdv_solve\.so(\.\d+)+$")

_BUILD_DIR_NAMES = ("build", "_build", "build_release", "cmake-build-release")


class SolverDiscoveryError(RuntimeError):
    """An installation was selected but cannot be compiled and linked
    against. Carries an actionable message naming it."""


class SolverPaths(NamedTuple):
    """Where the solver's artifacts are, for a compile/link command.

    ``include_dirs`` is a SEQUENCE because the installed layout needs two
    entries: dv-solve stages its headers under ``share/include/dv_solve/``,
    but its own headers and the generated solver code both use unqualified
    includes (``#include "dv_solve.h"``), which resolve only against the
    nested directory -- while a consumer writing ``dv_solve/dv_solve.h`` needs
    the base. A single directory could not express that.

    ``include_dir`` is retained as the first entry so existing callers keep
    working; it is the right answer for a source tree, where the headers are
    flat, and the wrong one for a wheel, so new code should use the plural.

    WHAT THESE ARE NOT: this is the include set for the SOLVER translation
    unit only, and must never be merged into one ``-I`` list with the
    backend's -- see ``driver.py``.
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


def _linkable_in(d: Path) -> Optional[Path]:
    """``libdv_solve.so`` in *d* if it is a real file or a symlink to one.

    ``is_file`` follows symlinks, so a directory of that name and a dangling
    link are both rejected.
    """
    p = d / _LINK_NAME
    return p if p.is_file() else None


def _versioned_in(d: Path) -> Optional[Path]:
    if not d.is_dir():
        return None
    hits = sorted((p for p in d.iterdir()
                   if _VERSIONED.match(p.name) and p.is_file()),
                  key=lambda p: (len(p.name), p.name))
    return hits[0] if hits else None


class _Candidate(NamedTuple):
    """One installation, as this module sees it."""
    what: str
    lib_dirs: List[Path]
    inc_sets: List[List[str]]

    def loadable(self) -> bool:
        return any(_linkable_in(d) or _versioned_in(d) for d in self.lib_dirs)

    def paths(self) -> SolverPaths:
        """The selected installation's paths, or :class:`SolverDiscoveryError`.

        Never looks at another installation for what this one lacks.
        """
        lib = next((l for l in map(_linkable_in, self.lib_dirs) if l), None)
        if lib is None:
            versioned = next((v for v in map(_versioned_in, self.lib_dirs)
                              if v), None)
            if versioned is not None:
                raise SolverDiscoveryError(
                    "dv-solve: the selected installation (%s) holds %s, which "
                    "can be loaded but which -ldv_solve cannot resolve: there "
                    "is no %s beside it.\nOther installations are not "
                    "consulted.\nFixes:\n  - add the linker name (e.g. "
                    "ln -s %s %s)\n  - or set ZSP_SOLVER_PATH to a complete "
                    "installation." % (self.what, versioned, _LINK_NAME,
                                       versioned.name, _LINK_NAME))
            raise SolverDiscoveryError(
                "dv-solve: the selected installation (%s) has no usable %s.\n"
                "Fixes:\n  - complete that installation, or set "
                "ZSP_SOLVER_PATH to a complete one." % (self.what, _LINK_NAME))
        for inc_set in self.inc_sets:
            incs = _usable_incdirs(inc_set)
            if incs is not None:
                return SolverPaths(lib_dir=lib.parent, include_dirs=incs)
        raise SolverDiscoveryError(
            "dv-solve: the selected installation (%s) has a library but no "
            "solver headers (%s).\nOther installations are not consulted.\n"
            "Fixes:\n  - complete that installation, or set ZSP_SOLVER_PATH "
            "to a complete one." % (self.what, _SENTINEL_HEADER))


def _select(cands: Sequence[_Candidate]) -> Optional[SolverPaths]:
    """First candidate holding a loadable library, validated; ``None`` if
    no candidate holds one."""
    for cand in cands:
        if cand.loadable():
            return cand.paths()
    return None


def _dv_solve_resolver():
    """dv-solve's installation API, or ``None`` when dv-solve is not
    importable or predates it."""
    try:
        from dv_solve import _resolve
    except ImportError:
        return None
    return _resolve if hasattr(_resolve, "select_installation") else None


def _from_env() -> Optional[SolverPaths]:
    """``ZSP_SOLVER_PATH``: a directory or a CMake install prefix. Terminal:
    raises rather than returning ``None`` when set but unusable."""
    root = os.environ.get("ZSP_SOLVER_PATH")
    if not root:
        return None
    base = Path(root)
    cand = _Candidate(
        "ZSP_SOLVER_PATH=%s" % root,
        [base, base / "lib", base / "lib64"],
        [[str(base)],
         [str(base / "include"), str(base / "include" / "dv_solve")],
         [str(base / "share" / "include"),
          str(base / "share" / "include" / "dv_solve")]])
    return cand.paths()


def _from_resolver(resolver) -> Optional[SolverPaths]:
    """Delegate to dv-solve's own installation contract."""
    inst = resolver.select_installation()
    if inst is None:
        return None
    try:
        lib = resolver.require_library("dv_solve", linkable=True)
        incs = resolver.require_incdirs()
    except RuntimeError as e:
        raise SolverDiscoveryError(str(e)) from e
    # Checked again here rather than trusted: the build command is ours.
    lib_dir = Path(lib).parent
    if _linkable_in(lib_dir) is None or _usable_incdirs(incs) is None:
        raise SolverDiscoveryError(
            "dv-solve reported %s / %s, which do not hold %s and %s."
            % (lib_dir, incs, _LINK_NAME, _SENTINEL_HEADER))
    return SolverPaths(lib_dir=lib_dir, include_dirs=_usable_incdirs(incs))


def _from_package() -> Optional[SolverPaths]:
    """An importable dv_solve: its installation API if it has one, else the
    older ``get_libdirs()``/``get_incdirs()`` under the same rules."""
    resolver = _dv_solve_resolver()
    if resolver is not None:
        return _from_resolver(resolver)
    try:
        import dv_solve
    except ImportError:
        return None
    try:
        lib_dirs = dv_solve.get_libdirs()
        inc_dirs = dv_solve.get_incdirs()
    except RuntimeError as e:
        raise SolverDiscoveryError(str(e)) from e
    # get_libdirs() falls back to naming the package directory when nothing is
    # built, so its answer has to be verified rather than trusted. Older
    # releases report only the base of a wheel's include tree, whose headers
    # sit one level down in dv_solve/; the nested set is the same
    # installation, so it is not borrowing.
    inc_dirs = list(inc_dirs)
    return _select([_Candidate(
        "dv_solve package at %s" % os.path.dirname(dv_solve.__file__),
        [Path(d) for d in lib_dirs],
        [inc_dirs, inc_dirs + [os.path.join(d, "dv_solve") for d in inc_dirs]])])


def _find_dv_solve_root() -> Optional[Path]:
    """Walk up from this file to a ``packages/dv-solve`` checkout."""
    here = Path(__file__).resolve()
    for p in here.parents:
        for cand in (p / "dv-solve", p / "packages" / "dv-solve"):
            if (cand / "src" / "c" / _SENTINEL_HEADER).exists():
                return cand
    return None


def _from_checkout() -> Optional[SolverPaths]:
    """A sibling dv-solve checkout, one candidate per build directory."""
    root = _find_dv_solve_root()
    if root is None:
        return None
    cands = []
    for bd in _BUILD_DIR_NAMES:
        b = root / bd
        cands.append(_Candidate(
            "checkout build at %s" % b,
            [b / "lib", b / "lib64", b],
            [[str(root / "src" / "c")],
             [str(b / "include"), str(b / "include" / "dv_solve")]]))
    return _select(cands)


def find_solver_paths() -> Optional[SolverPaths]:
    """Locate dv-solve.

    Returns ``None`` if no installation exists; raises
    :class:`SolverDiscoveryError` if one was selected but is unusable.
    """
    resolver = _dv_solve_resolver()
    if resolver is not None:
        # Final either way: it applies ZSP_SOLVER_PATH itself, and a checkout
        # it did not select must not be linked behind its back.
        return _from_resolver(resolver)
    if os.environ.get("ZSP_SOLVER_PATH"):
        return _from_env()
    found = _from_package()
    if found is not None:
        return found
    return _from_checkout()


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

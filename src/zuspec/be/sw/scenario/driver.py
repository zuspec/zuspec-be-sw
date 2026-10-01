"""Public driver API for the PSS → C scenario flow (impl-plan C6).

``generate_c``      — render an already-lowered ``ScenarioModule`` to C files.
``generate_c_files``— end-to-end: PSS source files → lower → emit C files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional, Union

from .emitter import CEmitter
from .solver_paths import (find_solver_paths, solver_not_found_message,
                           SolverDiscoveryError)

PathLike = Union[str, os.PathLike]


def _is_solver_tu(src: PathLike) -> bool:
    """Does this translation unit compile against the dv-solve headers?

    Detected by content rather than by file name so that renaming what the
    emitter writes cannot silently put a solver TU back into the backend's
    include set.
    """
    from .emitter import _SOLVER_INCLUDES
    try:
        text = Path(src).read_text()
    except OSError:
        return False
    return any('#include "%s"' % h in text for h in _SOLVER_INCLUDES)


def _partition_sources(sources):
    """Split *sources* into ``(backend_tus, solver_tus)``.

    THE REASON THIS EXISTS: dv-solve's headers and be-sw's runtime headers
    used to collide -- both shipped a ``zsp_alloc.h`` declaring an incompatible
    ``struct zsp_alloc_s`` -- and compiling every source in ONE gcc invocation
    carrying both include sets left the choice to ``-I`` order. dv-solve now
    prefixes its names ``dvs_`` and exposes one public header, ``dv_solve.h``,
    which removes that clash, but a single shared include set would still let
    either project's internal headers shadow the other's.

    Compiling each TU with only the include set it is entitled to makes the
    separation structural instead of incidental.
    """
    backend, solver = [], []
    for s in sources:
        (solver if _is_solver_tu(s) else backend).append(Path(s))
    return backend, solver


def _compile_solver_objects(solver_tus, out: Path, paths, extra_includes=None):
    """Compile the solver TUs to objects with ONLY dv-solve's include set.

    Returns ``(objects, error_or_None)``. ``extra_includes`` carries the
    generated-code directory, which holds the emitted scenario header -- that
    header is deliberately kept free of both runtimes' headers so it can be
    included from either side.
    """
    import subprocess

    objs = []
    for src in solver_tus:
        obj = out / (Path(src).stem + ".solver.o")
        cmd = ["gcc", "-c", "-fPIC", "-g", "-O0", "-w"]
        cmd += ["-I%s" % d for d in (extra_includes or [])]
        cmd += ["-I%s" % d for d in paths.include_dirs]
        cmd += [str(src), "-o", str(obj)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return [], "solver translation unit %s failed to compile:\n%s" % (
                Path(src).name, r.stderr)
        objs.append(obj)
    return objs, None


def generate_c(module, ctx, output_dir: PathLike,
               header: str = "scenario_gen") -> List[Path]:
    """Render a lowered :class:`ScenarioModule` to ``.h``/``.c``/``main.c``.

    Runs the consolidated Layer-1 validator first, so all unsupported constructs
    are reported together (with source locations) before any C is emitted.
    Returns the list of ``.c`` source paths to hand to :class:`CCompiler`.
    """
    from zuspec.ir.core.xf import ScenarioValidator
    ScenarioValidator().check_module(module)
    return CEmitter(module, ctx, header=header).write(output_dir)


def generate_c_bridge(module, ctx, output_dir: PathLike,
                      header: str = "scenario_gen"):
    """Render a scenario in **bridge mode** for the DPI shared library.

    Forces timebase-mode emission (every coroutine a ``zsp_timebase`` task) and
    emits a generic ``zsp_scenario_spawn`` dispatcher instead of ``main`` — so
    the scenario links into ``libzsp_scenario.so`` with the bridge runtime.
    Returns ``(sources, action_ids)`` where ``action_ids`` maps export-action
    name → integer id (shared with the SV shim).
    """
    from zuspec.ir.core.xf import ScenarioValidator
    ScenarioValidator().check_module(module)
    em = CEmitter(module, ctx, header=header, bridge=True)
    sources = em.write(output_dir)
    return sources, em.export_action_ids()


def _cbridge_dir() -> Path:
    return Path(__file__).resolve().parent / "cbridge"


def build_dpi_library(sources, output_dir: PathLike,
                      so_name: str = "libzsp_scenario.so",
                      link_solver: Optional[bool] = None):
    """Build the scenario DPI shared library.

    Compiles the generated bridge-mode sources + the ``zsp_bridge`` runtime +
    the ``share/rt`` runtime (+ ``libdv_solve`` when the scenario solves) into a
    single ``.so`` exporting the generic ``zsp_bridge_*`` ABI. A SystemVerilog
    testbench links this ``.so`` (via DPI) and can re-build the PSS scenario
    without recompiling the SV.

    Returns ``(CompileResult, so_path, solver_paths_or_None)``.
    """
    import subprocess
    from zuspec.be.sw.compiler import CCompiler, CompileResult

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cc = CCompiler(output_dir=out)
    cbridge = _cbridge_dir()
    sources = [Path(s) for s in sources]

    need = link_solver
    if need is None:
        need = any("dvs_builder_create(" in Path(s).read_text() for s in sources)

    backend_tus, solver_tus = _partition_sources(sources)

    paths = None
    solver_objs = []
    if need:
        try:
            paths = find_solver_paths()
        except SolverDiscoveryError as e:
            # A selected installation that cannot be linked: report it, never
            # quietly build against some other installation instead.
            return (CompileResult(False, stderr=str(e)), None, None)
        if paths is None:
            return (CompileResult(False, stderr=solver_not_found_message()),
                    None, None)
        # Solver TUs are compiled first, alone, against dv-solve's headers
        # only -- see _partition_sources for why they must not see be-sw's.
        solver_objs, err = _compile_solver_objects(
            solver_tus, out, paths, extra_includes=[out])
        if err:
            return (CompileResult(False, stderr=err), None, None)
    else:
        # No solver: nothing should have been classified as a solver TU, but
        # if it was, it still has to be compiled, and the backend set is the
        # only one available.
        backend_tus += solver_tus

    cmd = ["gcc", "-shared", "-fPIC", "-O0", "-g", "-w",
           f"-I{cc.include_dir}", f"-I{cbridge}", f"-I{out}"]
    cmd += [str(s) for s in backend_tus]
    cmd.append(str(cbridge / "zsp_bridge.c"))
    cmd += [str(s) for s in cc.get_runtime_sources()]
    cmd += [str(o) for o in solver_objs]

    if need:
        cmd += [f"-L{paths.lib_dir}", f"-l{paths.lib_name}",
                f"-Wl,-rpath,{paths.lib_dir}"]

    so = out / so_name
    cmd += ["-o", str(so)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (CompileResult(r.returncode == 0, r.stdout, r.stderr), so, paths)


def generate_c_files(paths: List[PathLike], output_dir: PathLike,
                     root: Optional[str] = None,
                     exports: Optional[List[str]] = None,
                     header: str = "scenario_gen") -> List[Path]:
    """Parse PSS *paths*, lower to Layer 1, and emit C files.

    This wires the whole iteration-1 front half:
    ``fe-pss → PSSToScenarioPass → CEmitter``.
    """
    from zuspec.fe.pss import Parser
    from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
    from zuspec.ir.core.xf import PSSToScenarioPass

    parser = Parser()
    srcs = []
    for p in paths:
        text = Path(p).read_text()
        srcs.append((os.path.basename(str(p)), text))
    parser.parses(srcs)
    ctx = AstToIrTranslator().translate(parser.link(),
                                        annotations=parser.annotations)
    if ctx.errors:
        raise ValueError("PSS translation errors: %s" % ctx.errors)

    module = PSSToScenarioPass(root=root, exports=exports).lower(ctx)
    return generate_c(module, ctx, output_dir, header=header)


def _needs_solver(sources) -> bool:
    for s in sources:
        try:
            if "dvs_builder_create(" in Path(s).read_text():
                return True
        except OSError:
            pass
    return False


def build_executable(sources, output: PathLike, output_dir: PathLike,
                     link_solver: Optional[bool] = None):
    """Compile emitted scenario sources to an executable, linking dv-solve when
    the generated C uses the solver.

    Returns ``(CompileResult, solver_paths_or_None)``.  When the solver is
    needed but cannot be located, returns a failed ``CompileResult`` with a
    clear message (callers skip-with-reason).
    """
    from zuspec.be.sw.compiler import CCompiler, CompileResult

    need = _needs_solver(sources) if link_solver is None else link_solver
    cc = CCompiler(output_dir=output_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    extra_includes = [out]
    lib_dirs = libs = rpaths = None
    paths = None

    backend_tus, solver_tus = _partition_sources(sources)
    solver_objs = []
    if need:
        try:
            paths = find_solver_paths()
        except SolverDiscoveryError as e:
            return (CompileResult(False, stderr=str(e)), None)
        if paths is None:
            return (CompileResult(False, stderr=solver_not_found_message()),
                    None)
        # Compiled separately, against dv-solve's headers only. Passing the
        # solver include dirs to cc.compile() instead would not be equivalent:
        # CCompiler puts its own -I first and unconditionally, so the solver TU
        # would always see be-sw's headers ahead of dv-solve's. See
        # _partition_sources.
        solver_objs, err = _compile_solver_objects(
            solver_tus, out, paths, extra_includes=[out])
        if err:
            return (CompileResult(False, stderr=err), None)
        lib_dirs = [paths.lib_dir]
        rpaths = [paths.lib_dir]
        libs = [paths.lib_name]
    else:
        backend_tus += solver_tus

    result = cc.compile(backend_tus + solver_objs, Path(output),
                        extra_includes=extra_includes,
                        lib_dirs=lib_dirs, libs=libs, rpaths=rpaths)
    return (result, paths)

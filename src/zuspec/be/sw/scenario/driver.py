"""Public driver API for the PSS → C scenario flow (impl-plan C6).

``generate_c``      — render an already-lowered ``ScenarioModule`` to C files.
``generate_c_files``— end-to-end: PSS source files → lower → emit C files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional, Union

from .emitter import CEmitter
from .solver_paths import find_solver_paths

PathLike = Union[str, os.PathLike]


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
        need = any("solve_problem_init(" in Path(s).read_text() for s in sources)

    cmd = ["gcc", "-shared", "-fPIC", "-O0", "-g", "-w",
           f"-I{cc.include_dir}", f"-I{cbridge}", f"-I{out}"]
    cmd += [str(s) for s in sources]
    cmd.append(str(cbridge / "zsp_bridge.c"))
    cmd += [str(s) for s in cc.get_runtime_sources()]

    paths = None
    if need:
        paths = find_solver_paths()
        if paths is None:
            return (CompileResult(
                False, stderr="dv-solve not found; set ZSP_SOLVER_PATH or build "
                "packages/dv-solve"), None, None)
        cmd += [f"-I{paths.include_dir}", f"-L{paths.lib_dir}",
                f"-l{paths.lib_name}", f"-Wl,-rpath,{paths.lib_dir}"]

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
            if "solve_problem_init(" in Path(s).read_text():
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
    extra_includes = [Path(output_dir)]
    lib_dirs = libs = rpaths = None
    paths = None
    if need:
        paths = find_solver_paths()
        if paths is None:
            return (CompileResult(
                False, stderr="dv-solve library not found; set ZSP_SOLVER_PATH "
                "or build packages/dv-solve (cmake -> build/)"), None)
        extra_includes.append(paths.include_dir)
        lib_dirs = [paths.lib_dir]
        rpaths = [paths.lib_dir]
        libs = [paths.lib_name]
    result = cc.compile([Path(s) for s in sources], Path(output),
                        extra_includes=extra_includes,
                        lib_dirs=lib_dirs, libs=libs, rpaths=rpaths)
    return (result, paths)

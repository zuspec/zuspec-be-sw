"""
ZuSpec Backend for SW (C) code generation.
"""
import ctypes
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory

from .c_generator import CGenerator
from .validator import CValidator, ValidationError
from .compiler import CCompiler, CompileResult
from .runner import TestRunner, TestResult
from .type_mapper import TypeMapper
from .stmt_generator import StmtGenerator
from .dm_async_generator import DmAsyncMethodGenerator
from .output import OutputManager, OutputFile

from .co_obj_factory import CObjFactory, ComponentProxy
from .ir.protocol import EvalProtocol
from .ir.base import SwContext

__all__ = [
    "CGenerator",
    "CValidator",
    "ValidationError",
    "CCompiler",
    "CompileResult",
    "TestRunner",
    "TestResult",
    "TypeMapper",
    "StmtGenerator",
    "DmAsyncMethodGenerator",
    "OutputManager",
    "OutputFile",
    "CObjFactory",
    "ComponentProxy",
    "EvalProtocol",
    "generate",
    "compile_and_load",
    "debug_session",
]

# Ordered RTL pass pipeline (run after ComponentClassifyPass determines RTL/MLS)
_RTL_PASSES = None


def _get_rtl_pipeline():
    """Lazily build the ordered RTL pass list."""
    global _RTL_PASSES
    if _RTL_PASSES is None:
        from .passes.rtl.component_classify import ComponentClassifyPass
        from .passes.rtl.next_state_split import NextStateSplitPass
        from .passes.rtl.comb_order import CombTopoSortPass
        from .passes.rtl.expr_lower import ExprLowerPass
        from .passes.rtl.pipeline_lower import PipelineLowerPass
        from .passes.rtl.wait_lower import WaitLowerPass
        from .passes.rtl.c_emit import RtlCEmitPass
        _RTL_PASSES = [
            ComponentClassifyPass,
            NextStateSplitPass,
            CombTopoSortPass,
            ExprLowerPass,
            PipelineLowerPass,
            WaitLowerPass,
            RtlCEmitPass,
        ]
    return _RTL_PASSES


def _build_rtl_context(
    component_class: type,
    *,
    domain_period_ps: int = 10_000,
    tier: Optional[int] = None,
    debug: bool = False,
) -> SwContext:
    """Build a SwContext populated with RTL-specific fields."""
    dmf = DataModelFactory()
    build_ctx = dmf.build(component_class)
    name = component_class.__qualname__
    comp_ir = build_ctx.type_m[name]

    _mod = sys.modules.get(component_class.__module__, None)
    _module_globals = _mod.__dict__ if _mod is not None else {}

    ctx = SwContext(type_m=dict(build_ctx.type_m))
    ctx.rtl_component = comp_ir
    ctx.rtl_component_class = component_class
    ctx.rtl_domain_period_ps = domain_period_ps
    ctx.rtl_debug = debug
    ctx.py_globals = _module_globals
    if tier is not None:
        ctx.rtl_tier = tier
    return ctx


def _run_rtl_pipeline(ctx: SwContext) -> SwContext:
    """Run the full RTL pass pipeline on *ctx*."""
    for pass_cls in _get_rtl_pipeline():
        ctx = pass_cls().run(ctx)
    return ctx


def generate(
    component_class: type,
    output_dir: "str | Path",
    *,
    domain_period_ps: int = 10_000,
    tier: Optional[int] = None,
    debug: bool = False,
) -> List[Path]:
    """Run the RTL pass pipeline and write generated files.

    Works for any Zuspec RTL component (``@sync`` / ``@comb``).  The
    execution protocol is auto-detected by ``ComponentClassifyPass``.

    Parameters
    ----------
    component_class:
        A ``@zdc.dataclass`` component class.
    output_dir:
        Directory to write generated files into.
    domain_period_ps:
        Primary clock period in picoseconds (default 10 ns).
    tier:
        Override tier detection (0, 1, or 2).  ``None`` → auto-detect.
    debug:
        When ``True``, emit ``#line`` directives, coroutine frame registry
        fields, source map, and embedded GDB script in the generated output.

    Returns
    -------
    List of ``Path`` objects for every file written.
    """
    import shutil as _shutil

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ctx = _build_rtl_context(
        component_class,
        domain_period_ps=domain_period_ps,
        tier=tier,
        debug=debug,
    )
    ctx = _run_rtl_pipeline(ctx)

    written: List[Path] = []
    for filename, content in ctx.output_files:
        p = output_dir / filename
        p.write_text(content)
        written.append(p)

    # Copy runtime headers alongside generated files
    _share_include = Path(__file__).parent / "share" / "include"
    for _hdr in _share_include.glob("zsp_rtl*.h"):
        dest = output_dir / _hdr.name
        _shutil.copy(_hdr, dest)
        if dest not in written:
            written.append(dest)

    return written


def compile_and_load(
    component_class: type,
    output_dir: "str | Path",
    *,
    extra_compile_flags: "list[str] | None" = None,
    debug: bool = False,
    domain_period_ps: int = 10_000,
    tier: Optional[int] = None,
) -> Tuple[ctypes.CDLL, type]:
    """``generate()`` + compile to a shared library + load via ctypes.

    Parameters
    ----------
    component_class:
        A ``@zdc.dataclass`` component class.
    output_dir:
        Directory for generated + compiled artifacts.
    extra_compile_flags:
        Additional flags passed to ``cc``.
    debug:
        When ``True``, compile with ``-g -DZS_DEBUG`` and include the
        ``zsp_rtl_debug.c`` runtime.
    domain_period_ps:
        Primary clock period in picoseconds.
    tier:
        Override RTL tier detection.

    Returns
    -------
    ``(lib, State)`` — the loaded ``ctypes.CDLL`` and the auto-generated
    ``ctypes.Structure`` subclass for the component state.
    """
    import shutil as _shutil

    output_dir = Path(output_dir)
    paths = generate(
        component_class,
        output_dir,
        debug=debug,
        domain_period_ps=domain_period_ps,
        tier=tier,
    )

    # When debug=True, also copy the debug runtime .c into the output dir
    if debug:
        _share_rt = Path(__file__).parent / "share" / "rt"
        _debug_c_src = _share_rt / "zsp_rtl_debug.c"
        if _debug_c_src.exists():
            _debug_c_dst = output_dir / "zsp_rtl_debug.c"
            if not _debug_c_dst.exists():
                _shutil.copy(_debug_c_src, _debug_c_dst)
            if _debug_c_dst not in paths:
                paths.append(_debug_c_dst)

    name = component_class.__name__
    so_path = output_dir / f"{name}.so"
    c_files = [str(p) for p in paths if str(p).endswith(".c")]
    h_dirs = list({str(p.parent) for p in paths if str(p).endswith(".h")})

    include_flags = ["-I", str(output_dir)]
    for d in h_dirs:
        if d != str(output_dir):
            include_flags += ["-I", d]

    opt_flags = ["-O3", "-fno-semantic-interposition"]
    if debug:
        opt_flags += ["-g", "-DZS_DEBUG"]
    if extra_compile_flags:
        opt_flags += extra_compile_flags

    subprocess.check_call(
        ["cc"] + opt_flags + ["-shared", "-fPIC", "-o", str(so_path)]
        + c_files
        + include_flags
    )

    lib = ctypes.CDLL(str(so_path))

    ctypes_file = output_dir / f"{name}_ctypes.py"
    ns: dict = {}
    exec(ctypes_file.read_text(), ns)

    return lib, ns["State"]


def debug_session(
    component_class: type,
    output_dir: "str | Path",
    **kwargs,
) -> Tuple[ctypes.CDLL, type]:
    """Convenience: ``compile_and_load()`` with ``debug=True``.

    Equivalent to ``compile_and_load(component_class, output_dir, debug=True, ...)``.
    Returns ``(lib, State)`` compiled with ``-g -DZS_DEBUG``, embedded source
    map, and auto-loading GDB script.
    """
    return compile_and_load(component_class, output_dir, debug=True, **kwargs)

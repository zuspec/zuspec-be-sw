"""PSS scenario backend — Layer-1 (``scenario`` dialect) → C.

See ``design/pss-lowering-impl-plan.md`` (Phase 2+).  The datamodel-driven
``CGenerator`` is independent of this path and untouched.
"""
from .driver import (
    generate_c, generate_c_files, build_executable,
    generate_c_bridge, build_dpi_library,
)
from .emitter import CEmitter
from .stmt_gen import ScenarioStmtGenerator
from .solver_paths import find_solver_paths, SolverPaths
from .sv_shim import generate_sv_shim

__all__ = [
    "generate_c",
    "generate_c_files",
    "build_executable",
    "generate_c_bridge",
    "build_dpi_library",
    "generate_sv_shim",
    "CEmitter",
    "ScenarioStmtGenerator",
    "find_solver_paths",
    "SolverPaths",
]

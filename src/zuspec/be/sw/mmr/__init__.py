"""``zuspec.be.sw.mmr`` — MMR software artefact generators.

Public API
----------
:func:`emit_c_header`
    Generate a C header with ``#define`` macros for register offsets,
    field shifts/masks, and access macros.

:func:`emit_py_driver`
    Generate a Python driver class with typed field-level accessors.
"""
from .c_header  import MmrRegFileCHeaderEmitter, emit_c_header
from .py_driver import MmrRegFilePyDriverEmitter, emit_py_driver

__all__ = [
    "MmrRegFileCHeaderEmitter",
    "emit_c_header",
    "MmrRegFilePyDriverEmitter",
    "emit_py_driver",
]

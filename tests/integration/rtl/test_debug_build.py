"""Integration tests for the debug build pipeline.

Verifies that compile_and_load(debug=True) and debug_session() produce a valid
shared library with:
  - ELF sections .zuspec_srcmap and .debug_gdb_scripts (via readelf)
  - Functional simulation still works after debug flags are applied
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_counter():
    examples = Path(__file__).parents[5] / "examples" / "01_counter"
    if str(examples) not in sys.path:
        sys.path.insert(0, str(examples))
    import counter as _m
    return _m.Counter


def _readelf_sections(so_path: str) -> set:
    try:
        out = subprocess.check_output(
            ["readelf", "-S", "-W", so_path], stderr=subprocess.DEVNULL, text=True
        )
        secs = set()
        for line in out.splitlines():
            if "]" not in line:
                continue
            rest = line.split("]", 1)[-1].strip()
            if rest:
                name = rest.split()[0]
                secs.add(name)
        return secs
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDebugBuild:
    """End-to-end debug build and artifact validation."""

    def test_debug_session_returns_lib_and_state(self):
        """debug_session() should return (CDLL, CtypesState)."""
        from zuspec.be.sw import debug_session
        Counter = _find_counter()
        with tempfile.TemporaryDirectory() as td:
            lib, State = debug_session(Counter, td)
        assert isinstance(lib, ctypes.CDLL)
        assert issubclass(State, ctypes.Structure)

    def test_compile_so_debug_functional(self):
        """Debug build should still produce correct simulation results."""
        from zuspec.be.sw import compile_and_load
        Counter = _find_counter()
        with tempfile.TemporaryDirectory() as td:
            lib, State = compile_and_load(Counter, td, debug=True)
            s = State()
            lib.Counter_init(ctypes.byref(s))
            s.enable = 1
            for _ in range(5):
                lib.Counter_clock_edge(ctypes.byref(s))
                lib.Counter_eval_comb(ctypes.byref(s))
                lib.Counter_advance(ctypes.byref(s))
            assert s._regs.count == 5

    def test_debug_build_has_srcmap_section(self):
        """The compiled .so must contain a .zuspec_srcmap ELF section."""
        from zuspec.be.sw import compile_and_load
        Counter = _find_counter()
        with tempfile.TemporaryDirectory() as td:
            lib, State = compile_and_load(Counter, td, debug=True)
            so_path = Path(td) / "Counter.so"
            secs = _readelf_sections(str(so_path))
        if not secs:
            pytest.skip("readelf not available")
        assert ".zuspec_srcmap" in secs, f"Sections: {secs}"

    def test_debug_build_has_gdb_scripts_section(self):
        """The compiled .so must contain a .debug_gdb_scripts ELF section."""
        from zuspec.be.sw import compile_and_load
        Counter = _find_counter()
        with tempfile.TemporaryDirectory() as td:
            lib, State = compile_and_load(Counter, td, debug=True)
            so_path = Path(td) / "Counter.so"
            secs = _readelf_sections(str(so_path))
        if not secs:
            pytest.skip("readelf not available")
        assert ".debug_gdb_scripts" in secs, f"Sections: {secs}"

    def test_generate_debug_creates_srcmap_c(self):
        """generate(debug=True) must write a *_srcmap.c file."""
        from zuspec.be.sw import generate
        Counter = _find_counter()
        with tempfile.TemporaryDirectory() as td:
            paths = generate(Counter, td, debug=True)
        names = [p.name for p in paths]
        assert any(n.endswith("_srcmap.c") for n in names), f"Files: {names}"

    def test_generate_debug_creates_debug_c(self):
        """generate(debug=True) must write a *_debug.c file."""
        from zuspec.be.sw import generate
        Counter = _find_counter()
        with tempfile.TemporaryDirectory() as td:
            paths = generate(Counter, td, debug=True)
        names = [p.name for p in paths]
        assert any(n.endswith("_debug.c") for n in names), f"Files: {names}"

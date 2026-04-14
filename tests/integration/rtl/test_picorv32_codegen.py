"""
Integration test: PicoRV32 Zuspec model generates and compiles to C.

Requires zpicorv32 to be available at:
  ../../../zuspec-example-mls-riscv/zpicorv32
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PICORV32_DIR = Path(__file__).parents[5] / "zuspec-example-mls-riscv" / "zpicorv32"
INCLUDE_DIR  = Path(__file__).parents[2] / "src" / "zuspec" / "be" / "rtl" / "include"


@pytest.fixture(scope="module")
def picorv32_class():
    if not PICORV32_DIR.exists():
        pytest.skip(f"zpicorv32 not found at {PICORV32_DIR}")
    if str(PICORV32_DIR) not in sys.path:
        sys.path.insert(0, str(PICORV32_DIR))
    from picorv32 import PicoRV32  # type: ignore
    return PicoRV32


def test_picorv32_generates(picorv32_class, tmp_path):
    """PicoRV32.c and PicoRV32.h are produced without error."""
    from zuspec.be.sw import generate
    written = generate(picorv32_class, tmp_path)
    names = {p.name for p in written}
    assert "PicoRV32.c" in names
    assert "PicoRV32.h" in names
    assert (tmp_path / "PicoRV32.c").stat().st_size > 1000


def test_picorv32_compiles(picorv32_class, tmp_path):
    """Generated PicoRV32.c compiles cleanly with gcc."""
    from zuspec.be.sw import generate
    generate(picorv32_class, tmp_path)

    result = subprocess.run(
        [
            "gcc", "-O2", "-shared", "-fPIC",
            "-o", str(tmp_path / "PicoRV32.so"),
            str(tmp_path / "PicoRV32.c"),
            "-I", str(INCLUDE_DIR),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Compilation failed:\n{result.stderr}")
    assert (tmp_path / "PicoRV32.so").exists()

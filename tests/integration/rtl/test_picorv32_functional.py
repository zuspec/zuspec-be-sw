"""
Functional test for the PicoRV32 Zuspec model compiled to C.

Runs a tiny RV32I program:
    addi x1, x0, 42
    sw   x1, 0x100(x0)
    ebreak

Expects:
  - store to address 0x100 with value 42
  - CPU trap (ebreak)
"""
import ctypes
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to zpicorv32 relative to repo root
_ZPICORV32_DIR = Path(__file__).parents[5] / "zuspec-example-mls-riscv" / "zpicorv32"


def _zpicorv32_available():
    return (_ZPICORV32_DIR / "picorv32.py").exists()


skip_no_zpicorv32 = pytest.mark.skipif(
    not _zpicorv32_available(),
    reason=f"zpicorv32 not found at {_ZPICORV32_DIR}",
)

# ---------------------------------------------------------------------------
# Session-scoped fixture: build .so once
# ---------------------------------------------------------------------------

_SO_TMPDIR = None
_SO_PATH = None
_CTYPES_MOD = None


def _ensure_built():
    """Build PicoRV32.so on first call; return (so_path, ctypes_module)."""
    global _SO_TMPDIR, _SO_PATH, _CTYPES_MOD
    if _SO_PATH is not None:
        return _SO_PATH, _CTYPES_MOD

    sys.path.insert(0, str(_ZPICORV32_DIR))
    from picorv32 import PicoRV32  # noqa: PLC0415

    from zuspec.be.sw import generate  # noqa: PLC0415

    _SO_TMPDIR = tempfile.mkdtemp(prefix="picorv32_test_")
    tmpdir = _SO_TMPDIR

    generate(PicoRV32, tmpdir)

    rt_include = Path(__file__).parents[3] / "src" / "zuspec" / "be" / "rtl" / "rt"
    so_path = Path(tmpdir) / "PicoRV32.so"
    ret = subprocess.run(
        [
            "gcc", "-O2", "-shared", "-fPIC",
            f"-I{rt_include}",
            str(Path(tmpdir) / "PicoRV32.c"),
            "-o", str(so_path),
        ],
        capture_output=True,
        text=True,
    )
    assert ret.returncode == 0, f"gcc failed:\n{ret.stderr}"

    # Load ctypes wrapper
    sys.path.insert(0, tmpdir)
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "PicoRV32_ctypes", Path(tmpdir) / "PicoRV32_ctypes.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    _SO_PATH = str(so_path)
    _CTYPES_MOD = mod
    return _SO_PATH, _CTYPES_MOD


def _make_cpu():
    """Return (lib, cpu_State_instance) ready to use."""
    so_path, mod = _ensure_built()
    lib = ctypes.CDLL(so_path)
    lib.PicoRV32_init.argtypes = [ctypes.POINTER(mod.State)]
    lib.PicoRV32_init.restype = None
    lib.PicoRV32_clock_edge.argtypes = [ctypes.POINTER(mod.State)]
    lib.PicoRV32_clock_edge.restype = None

    cpu = mod.State()
    lib.PicoRV32_init(ctypes.byref(cpu))
    return lib, cpu


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@skip_no_zpicorv32
def test_picorv32_const_defaults():
    """zdc.const fields must be initialized to their Python defaults in _init."""
    _lib, cpu = _make_cpu()

    assert cpu.ENABLE_REGS_DUALPORT == 1, "ENABLE_REGS_DUALPORT must be 1"
    assert cpu.CATCH_ILLINSN == 1, "CATCH_ILLINSN must be 1"
    assert cpu.CATCH_MISALIGN == 1, "CATCH_MISALIGN must be 1"
    assert cpu.TWO_STAGE_SHIFT == 1, "TWO_STAGE_SHIFT must be 1"
    assert cpu.STACKADDR == 0xFFFFFFFF, "STACKADDR must be 0xFFFFFFFF"


@skip_no_zpicorv32
def test_picorv32_addi_sw_ebreak():
    """Run addi/sw/ebreak program; expect store to 0x100 with value 42 + trap."""
    lib, cpu = _make_cpu()
    _, mod = _ensure_built()

    # Simple flat memory (512 words)
    Mem = (ctypes.c_uint32 * 512)
    mem = Mem()
    mem[0] = 0x02A00093   # addi x1, x0, 42
    mem[1] = 0x10102023   # sw   x1, 0x100(x0)
    mem[2] = 0x00100073   # ebreak

    def clock():
        lib.PicoRV32_clock_edge(ctypes.byref(cpu))

    # Reset
    cpu.resetn = 0
    for _ in range(4):
        clock()
    cpu.resetn = 1

    stored = False
    trapped = False
    for _cycle in range(300):
        if cpu.mem_valid and not cpu.mem_ready:
            addr = cpu.mem_addr
            idx = (addr >> 2) & 0x1FF
            if cpu.mem_wstrb == 0:
                cpu.mem_rdata = mem[idx]
                cpu.mem_ready = 1
            else:
                wdata = cpu.mem_wdata
                wstrb = cpu.mem_wstrb
                idx = (addr >> 2) & 0x1FF
                new_val = mem[idx]
                if wstrb & 1: new_val = (new_val & ~0xFF) | (wdata & 0xFF)
                if wstrb & 2: new_val = (new_val & ~0xFF00) | (wdata & 0xFF00)
                if wstrb & 4: new_val = (new_val & ~0xFF0000) | (wdata & 0xFF0000)
                if wstrb & 8: new_val = (new_val & ~0xFF000000) | (wdata & 0xFF000000)
                mem[idx] = new_val
                if addr == 0x100:
                    stored = True
                cpu.mem_ready = 1

        clock()
        cpu.mem_ready = 0

        if cpu.trap:
            trapped = True
            break

    assert stored, "Expected store to 0x100"
    assert mem[0x100 >> 2] == 42, f"Expected value 42 at 0x100, got {mem[0x100>>2]}"
    assert trapped, "Expected CPU trap (ebreak)"


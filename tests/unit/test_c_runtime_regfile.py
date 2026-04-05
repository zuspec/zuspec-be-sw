"""Tests for IndexedRegFile and IndexedPool lowering via CObjFactory (Phase 4).

Verifies:
- Struct contains C array of correct width for IndexedRegFile
- _get / _set / _read_all accessor functions generated and callable
- ComponentProxy exposes regfile as _RegFileProxy with [] access
- IndexedPool struct field uses zsp_indexed_pool_t (not a raw array)
- zsp_indexed_pool_init called in _init function
"""
from __future__ import annotations

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fixtures"))

try:
    from zuspec.be.sw import CObjFactory
    from zuspec.be.sw.co_obj_factory import _RegFileProxy
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

pytestmark = pytest.mark.skipif(not HAS_BACKEND, reason="zuspec.be.sw not available")


@pytest.fixture(scope="module")
def minicore_proxy():
    from minicore_component import MiniCore
    factory = CObjFactory()
    return factory.mkComponent(MiniCore)


# ---------------------------------------------------------------------------
# Generated C code inspection (CEmitPass output)
# ---------------------------------------------------------------------------

def test_regfile_struct_uses_c_array():
    """IndexedRegFile[u5, u32] → uint32_t regfile[32] in struct."""
    import tempfile
    from pathlib import Path
    from minicore_component import MiniCore
    from zuspec.dataclasses.data_model_factory import DataModelFactory
    from zuspec.be.sw.pipeline import SwPassManager
    from zuspec.be.sw.passes.c_emit import CEmitPass

    ir_ctx = DataModelFactory().build(MiniCore)
    sw_ctx = SwPassManager().run(ir_ctx)
    # Struct definition is now in the header (for sub-component embedding)
    hdr = {n: c for n, c in sw_ctx.output_files}.get("MiniCore.h", "")
    assert "uint32_t regfile[32]" in hdr


def test_regfile_read_fn_generated():
    """CEmitPass emits {name}_regfile_get(self, idx) in header and source."""
    from minicore_component import MiniCore
    from zuspec.dataclasses.data_model_factory import DataModelFactory
    from zuspec.be.sw.pipeline import SwPassManager

    ir_ctx = DataModelFactory().build(MiniCore)
    sw_ctx = SwPassManager().run(ir_ctx)
    files = {n: c for n, c in sw_ctx.output_files}
    assert "MiniCore_regfile_get" in files.get("MiniCore.h", "")
    assert "MiniCore_regfile_get" in files.get("MiniCore.c", "")


def test_regfile_write_fn_generated():
    """CEmitPass emits {name}_regfile_set(self, idx, val) in header and source."""
    from minicore_component import MiniCore
    from zuspec.dataclasses.data_model_factory import DataModelFactory
    from zuspec.be.sw.pipeline import SwPassManager

    ir_ctx = DataModelFactory().build(MiniCore)
    sw_ctx = SwPassManager().run(ir_ctx)
    files = {n: c for n, c in sw_ctx.output_files}
    assert "MiniCore_regfile_set" in files.get("MiniCore.h", "")
    assert "MiniCore_regfile_set" in files.get("MiniCore.c", "")


def test_indexed_pool_uses_zsp_type():
    """IndexedPool struct field uses zsp_indexed_pool_t, not a raw array."""
    from minicore_component import MiniCore
    from zuspec.dataclasses.data_model_factory import DataModelFactory
    from zuspec.be.sw.pipeline import SwPassManager

    ir_ctx = DataModelFactory().build(MiniCore)
    sw_ctx = SwPassManager().run(ir_ctx)
    # Struct definition is now in the header (for sub-component embedding)
    hdr = {n: c for n, c in sw_ctx.output_files}.get("MiniCore.h", "")
    assert "zsp_indexed_pool_t rd_sched" in hdr
    # Should NOT use a raw C array for the pool
    assert "uint32_t rd_sched[" not in hdr
    assert "uint8_t rd_sched[" not in hdr


def test_indexed_pool_init_called():
    """_init function calls zsp_indexed_pool_init for the pool field."""
    from minicore_component import MiniCore
    from zuspec.dataclasses.data_model_factory import DataModelFactory
    from zuspec.be.sw.pipeline import SwPassManager

    ir_ctx = DataModelFactory().build(MiniCore)
    sw_ctx = SwPassManager().run(ir_ctx)
    src = {n: c for n, c in sw_ctx.output_files}.get("MiniCore.c", "")
    assert "zsp_indexed_pool_init(&self->rd_sched" in src


# ---------------------------------------------------------------------------
# Runtime access via ComponentProxy
# ---------------------------------------------------------------------------

def test_regfile_proxy_type(minicore_proxy):
    """comp.regfile returns a _RegFileProxy, not a plain int."""
    rf = minicore_proxy.regfile
    assert isinstance(rf, _RegFileProxy), f"Expected _RegFileProxy, got {type(rf)}"


def test_regfile_read_write_roundtrip(minicore_proxy):
    """Write a value to regfile[5], read it back."""
    minicore_proxy.regfile[5] = 42
    assert minicore_proxy.regfile[5] == 42


def test_regfile_all_registers_accessible(minicore_proxy):
    """All 32 registers can be written and read back."""
    for i in range(32):
        minicore_proxy.regfile[i] = i * 100
    for i in range(32):
        assert minicore_proxy.regfile[i] == i * 100, f"reg[{i}] mismatch"


def test_regfile_index_masking(minicore_proxy):
    """Out-of-range index is masked to depth-1 (no crash, wraps around)."""
    minicore_proxy.regfile[0] = 0xABCD
    # Index 32 wraps to 0 (32 & 31 == 0)
    val = minicore_proxy.regfile[32]
    assert val == 0xABCD


def test_regfile_write_32bit_value(minicore_proxy):
    """Full 32-bit values survive the write/read cycle."""
    minicore_proxy.regfile[31] = 0xDEAD_BEEF
    assert minicore_proxy.regfile[31] == 0xDEAD_BEEF


def test_regfile_zero_initialised(minicore_proxy):
    """After init, all registers read as zero."""
    from minicore_component import MiniCore
    factory = CObjFactory()
    fresh = factory.mkComponent(MiniCore)
    for i in range(32):
        assert fresh.regfile[i] == 0, f"reg[{i}] not zeroed after init"

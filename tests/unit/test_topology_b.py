"""Tests for Topology B: multiple components composed inside RVTestbench.

Topology B puts both MiniCore and MemComponent inside a single parent
(RVTestbench), generated C implementation, pure-C hot path.
Python touches only backdoor APIs for setup and inspection.
"""
from __future__ import annotations

import struct
import pytest

from zuspec.be.sw.co_obj_factory import CObjFactory

from fixtures.testbench_components import MemComponent, RVTestbench  # type: ignore[import]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pack_addi(rd: int, rs1: int, imm: int) -> int:
    """Pack an ADDI instruction (I-type, opcode 0x13)."""
    imm12 = imm & 0xFFF
    return (imm12 << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x13


def _ecall() -> int:
    return 0x00000073


def _load_words(mem_proxy, addr: int, words: list[int]) -> None:
    """Write a list of 32-bit words to memory starting at *addr*."""
    for i, w in enumerate(words):
        mem_proxy.write(addr + i * 4, w)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def factory(tmp_path):
    return CObjFactory(cache_dir=tmp_path)


# ---------------------------------------------------------------------------
# Topology B tests
# ---------------------------------------------------------------------------

class TestTopologyB:

    def test_compile_rv_testbench(self, factory):
        """RVTestbench can be compiled and returns a ComponentProxy."""
        tb = factory.mkComponent(RVTestbench)
        assert tb is not None

    def test_sub_component_proxy(self, factory):
        """tb.core returns a ComponentProxy for the MiniCore sub-component."""
        tb = factory.mkComponent(RVTestbench)
        core = tb.core
        assert core is not None
        # pc should be accessible (it's a plain accessible field)
        pc = core.pc
        assert pc == 0

    def test_mem_sub_component_proxy(self, factory):
        """tb.mem returns a ComponentProxy for the MemComponent sub-component."""
        tb = factory.mkComponent(RVTestbench)
        mem = tb.mem
        assert mem is not None

    def test_mem_backdoor_write_read(self, factory):
        """Backdoor memory write/read through the sub-component proxy."""
        tb = factory.mkComponent(RVTestbench)
        mem_proxy = tb.mem.mem  # MemComponent.mem (zdc.Memory)
        mem_proxy.write(0, 0xDEADBEEF)
        val = mem_proxy.read(0)
        assert val == 0xDEADBEEF

    def test_run_addi_instruction(self, factory):
        """Execute a single ADDI x1, x0, 42 instruction in pure C.

        Program layout (word-addressed, byte offset):
          0x00: addi x1, x0, 42
          0x04: ecall
        """
        tb = factory.mkComponent(RVTestbench)
        mem_proxy = tb.mem.mem

        # Write program
        addi = _pack_addi(rd=1, rs1=0, imm=42)
        mem_proxy.write(0, addi)
        mem_proxy.write(4, _ecall())

        # Run (single instruction per run() call for MiniCore)
        tb.run()

        # x0 is always 0, so addi x1, x0, 42 → x1 = 42
        core = tb.core
        x1 = core.regfile[1]
        assert x1 == 42

    def test_run_until_halted(self, factory):
        """Run two instructions (addi + ecall), verify halted flag set."""
        tb = factory.mkComponent(RVTestbench)
        mem_proxy = tb.mem.mem

        addi = _pack_addi(rd=2, rs1=0, imm=7)
        mem_proxy.write(0, addi)
        mem_proxy.write(4, _ecall())

        # Step 1: addi
        tb.run()
        assert tb.core.halted == 0  # not halted yet

        # Step 2: ecall sets halted
        tb.run()
        assert tb.core.halted != 0

    def test_mem_component_standalone(self, factory):
        """MemComponent can be compiled standalone and tested."""
        mc = factory.mkComponent(MemComponent)
        mem = mc.mem
        mem.write(100, 0xCAFE)
        assert mem.read(100) == 0xCAFE

    def test_generated_files_include_ptr_accessor(self, factory, tmp_path):
        """The generated .h file declares the _ptr_ accessor for sub-components."""
        from zuspec.be.sw.passes import SwPassManager
        from zuspec.dataclasses.data_model_factory import DataModelFactory

        ir_ctx = DataModelFactory().build(RVTestbench)
        sw_ctx = SwPassManager().run(ir_ctx, py_globals={})

        # Find the RVTestbench header
        header_content = None
        for fname, content in sw_ctx.output_files:
            if fname == "RVTestbench.h":
                header_content = content
                break

        assert header_content is not None, "RVTestbench.h not generated"
        assert "RVTestbench_ptr_core" in header_content
        assert "RVTestbench_ptr_mem" in header_content

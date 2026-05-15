"""Tests for zuspec.be.sw.mmr — Phase 6 MMR software artefact generators."""
import pytest
import zuspec.dataclasses as zdc
from zuspec.be.sw.mmr import emit_c_header, emit_py_driver


# ---------------------------------------------------------------------------
# Test register file definitions
# ---------------------------------------------------------------------------

@zdc.regfile
class SimpleRegs(zdc.RegisterFile):
    @zdc.reg(offset=0x00)
    class CTRL:
        enable: zdc.u1 = zdc.reg_field(sw=zdc.SW.RW, hw=zdc.HW.R, lsb=0)
        mode:   zdc.u2 = zdc.reg_field(sw=zdc.SW.RW, hw=zdc.HW.R, lsb=1)

    @zdc.reg(offset=0x04)
    class STATUS:
        busy: zdc.u1 = zdc.reg_field(sw=zdc.SW.RO, hw=zdc.HW.W, lsb=0)
        done: zdc.u1 = zdc.reg_field(sw=zdc.SW.RO, hw=zdc.HW.W, lsb=1)


@zdc.regfile
class MixedRegs(zdc.RegisterFile):
    @zdc.reg(offset=0x00)
    class CMD:
        start: zdc.u1 = zdc.FieldAttr.Pulse

    @zdc.reg(offset=0x04)
    class IRQ_STATUS:
        overflow: zdc.u1 = zdc.reg_field(
            sw=zdc.SW.RW, hw=zdc.HW.W, stickybit=True, onwrite='woclr', lsb=0)
        underrun: zdc.u1 = zdc.reg_field(
            sw=zdc.SW.RW, hw=zdc.HW.W, stickybit=True, onwrite='woclr', lsb=1)

    @zdc.reg(offset=0x08)
    class DATA_WO:
        payload: zdc.u16 = zdc.reg_field(sw=zdc.SW.WO, hw=zdc.HW.R, lsb=0)


# ===========================================================================
# C header tests
# ===========================================================================

class TestCHeaderBasics:

    def test_include_guard_present(self):
        h = emit_c_header(SimpleRegs)
        assert "#ifndef SIMPLE_REGS_H" in h
        assert "#define SIMPLE_REGS_H" in h
        assert "#endif" in h

    def test_custom_prefix(self):
        h = emit_c_header(SimpleRegs, prefix="MY_REGS")
        assert "#ifndef MY_REGS_H" in h

    def test_stdint_included(self):
        h = emit_c_header(SimpleRegs, include_stdint=True)
        assert "#include <stdint.h>" in h

    def test_no_stdint(self):
        h = emit_c_header(SimpleRegs, include_stdint=False)
        assert "#include <stdint.h>" not in h

    def test_source_comment(self):
        h = emit_c_header(SimpleRegs)
        assert "SimpleRegs" in h

    def test_custom_data_type(self):
        h = emit_c_header(SimpleRegs, data_type="uint16_t")
        assert "uint16_t" in h


class TestCHeaderOffsets:

    def test_ctrl_offset(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_CTRL_OFFSET" in h
        assert "0x00U" in h

    def test_status_offset(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_STATUS_OFFSET" in h
        assert "0x04U" in h

    def test_three_registers_all_offsets(self):
        h = emit_c_header(MixedRegs)
        assert "MIXED_REGS_CMD_OFFSET" in h
        assert "MIXED_REGS_IRQ_STATUS_OFFSET" in h
        assert "MIXED_REGS_DATA_WO_OFFSET" in h


class TestCHeaderFieldDefines:

    def test_ctrl_enable_shift(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_CTRL_ENABLE_SHIFT" in h
        assert "0U" in h   # lsb=0

    def test_ctrl_enable_mask(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_CTRL_ENABLE_MASK" in h
        # width=1 at lsb=0 → mask = (0x1U << SHIFT)
        assert "(0x1U << SIMPLE_REGS_CTRL_ENABLE_SHIFT)" in h

    def test_ctrl_mode_shift(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_CTRL_MODE_SHIFT" in h
        assert "1U" in h   # lsb=1

    def test_ctrl_mode_mask(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_CTRL_MODE_MASK" in h
        # width=2 → (0x3U << SHIFT)
        assert "(0x3U << SIMPLE_REGS_CTRL_MODE_SHIFT)" in h

    def test_status_busy_shift(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_STATUS_BUSY_SHIFT" in h

    def test_status_done_shift(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_STATUS_DONE_SHIFT" in h


class TestCHeaderAccessMacros:

    def test_rd_macro_present(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_RD(base, off)" in h

    def test_wr_macro_present(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_WR(base, off, val)" in h

    def test_rmw_macro_present(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_RMW(" in h


class TestCHeaderFieldMacros:

    def test_rw_field_has_rd_macro(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_CTRL_ENABLE_RD(base)" in h

    def test_rw_field_has_wr_macro(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_CTRL_ENABLE_WR(base, val)" in h

    def test_ro_field_has_rd_macro(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_STATUS_BUSY_RD(base)" in h

    def test_ro_field_has_no_wr_macro(self):
        h = emit_c_header(SimpleRegs)
        assert "SIMPLE_REGS_STATUS_BUSY_WR" not in h

    def test_wo_field_has_no_rd_macro(self):
        h = emit_c_header(MixedRegs)
        assert "MIXED_REGS_DATA_WO_PAYLOAD_RD" not in h

    def test_wo_field_has_wr_macro(self):
        h = emit_c_header(MixedRegs)
        assert "MIXED_REGS_DATA_WO_PAYLOAD_WR(base, val)" in h

    def test_woclr_field_has_clr_macro(self):
        h = emit_c_header(MixedRegs)
        assert "MIXED_REGS_IRQ_STATUS_OVERFLOW_CLR(base)" in h

    def test_woclr_field_no_wr_macro(self):
        h = emit_c_header(MixedRegs)
        # should not emit a generic _WR for woclr
        assert "MIXED_REGS_IRQ_STATUS_OVERFLOW_WR" not in h

    def test_woclr_field_still_readable(self):
        h = emit_c_header(MixedRegs)
        assert "MIXED_REGS_IRQ_STATUS_OVERFLOW_RD(base)" in h


# ===========================================================================
# Python driver tests
# ===========================================================================

class TestPyDriverBasics:

    def test_class_name_default(self):
        src = emit_py_driver(SimpleRegs)
        assert "class SimpleRegsDriver:" in src

    def test_class_name_custom(self):
        src = emit_py_driver(SimpleRegs, class_name="MyDriver")
        assert "class MyDriver:" in src

    def test_source_comment(self):
        src = emit_py_driver(SimpleRegs)
        assert "SimpleRegs" in src

    def test_imports_present(self):
        src = emit_py_driver(SimpleRegs)
        assert "import ctypes" in src
        assert "from typing import" in src

    def test_base_addr_constructor(self):
        src = emit_py_driver(SimpleRegs)
        assert "base_addr" in src
        assert "read_fn" in src
        assert "write_fn" in src

    def test_offset_consts(self):
        src = emit_py_driver(SimpleRegs)
        assert "CTRL_OFFSET" in src
        assert "STATUS_OFFSET" in src


class TestPyDriverRegMethods:

    def test_read_ctrl_method(self):
        src = emit_py_driver(SimpleRegs)
        assert "def read_CTRL(self)" in src

    def test_write_ctrl_method(self):
        src = emit_py_driver(SimpleRegs)
        assert "def write_CTRL(self, value" in src

    def test_read_status_method(self):
        src = emit_py_driver(SimpleRegs)
        assert "def read_STATUS(self)" in src

    def test_three_registers_all_methods(self):
        src = emit_py_driver(MixedRegs)
        assert "def read_CMD(self)" in src
        assert "def read_IRQ_STATUS(self)" in src
        assert "def read_DATA_WO(self)" in src


class TestPyDriverFieldMethods:

    def test_rw_field_has_get(self):
        src = emit_py_driver(SimpleRegs)
        assert "def get_CTRL_enable(self)" in src

    def test_rw_field_has_set(self):
        src = emit_py_driver(SimpleRegs)
        assert "def set_CTRL_enable(self, value" in src

    def test_ro_field_has_get(self):
        src = emit_py_driver(SimpleRegs)
        assert "def get_STATUS_busy(self)" in src

    def test_ro_field_has_no_set(self):
        src = emit_py_driver(SimpleRegs)
        assert "def set_STATUS_busy" not in src

    def test_ro_field_done_has_get(self):
        src = emit_py_driver(SimpleRegs)
        assert "def get_STATUS_done(self)" in src

    def test_wo_field_has_no_get(self):
        src = emit_py_driver(MixedRegs)
        assert "def get_DATA_WO_payload" not in src

    def test_wo_field_has_set(self):
        src = emit_py_driver(MixedRegs)
        assert "def set_DATA_WO_payload(self, value" in src

    def test_woclr_field_has_clr_method(self):
        src = emit_py_driver(MixedRegs)
        assert "def clr_IRQ_STATUS_overflow(self)" in src

    def test_woclr_field_has_no_set(self):
        src = emit_py_driver(MixedRegs)
        assert "def set_IRQ_STATUS_overflow" not in src

    def test_woclr_field_still_readable(self):
        src = emit_py_driver(MixedRegs)
        assert "def get_IRQ_STATUS_overflow(self)" in src

    def test_singlepulse_field_has_get_and_set(self):
        src = emit_py_driver(MixedRegs)
        assert "def get_CMD_start(self)" in src
        assert "def set_CMD_start(self, value" in src


class TestPyDriverExecution:
    """Compile and exec the generated driver to ensure it's valid Python."""

    def _compile(self, cls):
        src = emit_py_driver(cls)
        ns = {}
        exec(compile(src, "<generated>", "exec"), ns)
        return ns

    def test_simple_regs_compiles(self):
        self._compile(SimpleRegs)

    def test_mixed_regs_compiles(self):
        self._compile(MixedRegs)

    def test_driver_instantiates_with_fake_io(self):
        ns = self._compile(SimpleRegs)
        driver_cls = ns["SimpleRegsDriver"]
        mem = [0] * 16
        driver = driver_cls(
            base_addr=0,
            read_fn=lambda a: mem[a // 4],
            write_fn=lambda a, v: mem.__setitem__(a // 4, v),
        )
        assert driver is not None

    def test_driver_field_roundtrip(self):
        ns = self._compile(SimpleRegs)
        driver_cls = ns["SimpleRegsDriver"]
        mem = [0] * 16

        driver = driver_cls(
            base_addr=0,
            read_fn=lambda a: mem[a // 4],
            write_fn=lambda a, v: mem.__setitem__(a // 4, v),
        )
        driver.set_CTRL_enable(1)
        assert driver.get_CTRL_enable() == 1

    def test_driver_ro_read(self):
        ns = self._compile(SimpleRegs)
        driver_cls = ns["SimpleRegsDriver"]
        mem = [0b11, 0] * 8  # STATUS busy=1, done=1

        driver = driver_cls(
            base_addr=0,
            read_fn=lambda a: mem[a // 4],
            write_fn=lambda a, v: mem.__setitem__(a // 4, v),
        )
        # mem[0] = 0b11 → enable=1, mode[1:0]=1
        assert driver.get_CTRL_enable() == 1

    def test_driver_mixed_regs_clr_woclr(self):
        ns = self._compile(MixedRegs)
        driver_cls = ns["MixedRegsDriver"]
        mem = [0xFFFF_FFFF] * 16  # all bits set

        driver = driver_cls(
            base_addr=0,
            read_fn=lambda a: mem[a // 4],
            write_fn=lambda a, v: mem.__setitem__(a // 4, v),
        )
        # clr_IRQ_STATUS_overflow should write bit 0 to address 0x04 (mem[1])
        driver.clr_IRQ_STATUS_overflow()
        # mem[1] should have been written with the overflow mask
        assert mem[1] == 0x1  # overflow bit is bit 0


# ===========================================================================
# Emitter class API tests
# ===========================================================================

class TestEmitterClassAPI:

    def test_c_header_class_direct(self):
        from zuspec.be.sw.mmr import MmrRegFileCHeaderEmitter
        e = MmrRegFileCHeaderEmitter(SimpleRegs)
        h = e.emit()
        assert "SIMPLE_REGS_CTRL_OFFSET" in h

    def test_py_driver_class_direct(self):
        from zuspec.be.sw.mmr import MmrRegFilePyDriverEmitter
        e = MmrRegFilePyDriverEmitter(SimpleRegs)
        src = e.emit()
        assert "class SimpleRegsDriver:" in src

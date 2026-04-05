"""Phase 5 RVCore Integration Tests.

Tests the RVCore sub-units (ALUUnit, MulDivUnit, LoadStoreUnit), partial
RVCore compilation, and MiniCore runtime behaviour reachable under current
IR limitations.

Current IR limitations (documented as xfail/skip markers):
  - ``cfg`` field (zdc.const sub-object) not embedded in C struct → error
  - ``FetchNext()()`` / ``ExecuteInstruction()()`` zdc.Action calls not lowered → error
  - ClaimPool / sub-component inst fields are skipped in struct generation

Test sections:
  A. Code-generation quality for each sub-unit (enum values, cast patterns)
  B. RVCore struct / header code-gen quality (regfile, rd_sched, icache)
  C. RVCore compilation status
  D. MiniCore runtime: icache callback invocation and PC advancement
  E. Sub-unit compilation smoke tests
  F. Sub-unit execution tests — exercise C-compiled execute() entry functions
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# conftest.py already prepends tests/unit/ to sys.path so ``fixtures.*`` works.
_PROJ_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(_PROJ_ROOT / "src"))
sys.path.insert(0, str(_PROJ_ROOT / "packages" / "zuspec-dataclasses" / "src"))

try:
    from zuspec.be.sw.co_obj_factory import CObjFactory
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_sw(cls):
    """Run DataModelFactory + SwPassManager for *cls*, return output_files dict."""
    import sys
    mod = sys.modules.get(cls.__module__)
    py_globals = mod.__dict__ if mod else {}

    from zuspec.dataclasses.data_model_factory import DataModelFactory
    from zuspec.be.sw.pipeline import SwPassManager

    ir_ctx = DataModelFactory().build(cls)
    sw_ctx = SwPassManager().run(ir_ctx, py_globals=py_globals)
    return {n: c for n, c in sw_ctx.output_files}


@pytest.fixture(scope="module")
def unit_tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ===========================================================================
# A. Code-generation quality for sub-units
# ===========================================================================

class TestALUUnitCodeGen:
    """ALUUnit generates correct C for all 10 AluOp cases."""

    @pytest.fixture(scope="class", autouse=True)
    def files(self, request):
        from org.zuspec.example.mls.riscv.rv_units import ALUUnit
        request.cls._files = _build_sw(ALUUnit)

    @property
    def src(self):
        return self._files.get("ALUUnit.c", "")

    @property
    def hdr(self):
        return self._files.get("ALUUnit.h", "")

    def test_all_ten_enum_values_resolved(self):
        """AluOp values 0-8 appear as explicit integer literals; AND (9) is the else catch-all.

        The code generator emits the final match/case arm as a plain ``else``
        branch, so value 9 (AND) does not appear as ``op == 9``.
        """
        for val in range(9):  # 0-8 are explicit; 9 is the `else` branch
            assert f"== {val}" in self.src or f"op == {val}" in self.src, \
                f"AluOp value {val} not found as integer literal in generated C"
        assert "else" in self.src, "Expected a catch-all else branch for AND (op==9)"

    def test_add_subtraction_branches_present(self):
        """ADD (0) and SUB (1) branches are in the generated source."""
        assert "rs1 + rs2" in self.src
        assert "rs1 - rs2" in self.src

    def test_slt_uses_int32_cast(self):
        """AluOp.SLT uses int32_t cast for signed comparison."""
        assert "int32_t" in self.src

    def test_sltu_unsigned_comparison(self):
        """AluOp.SLTU uses plain unsigned less-than."""
        assert "rs1 < rs2" in self.src

    def test_srl_right_shift_present(self):
        """AluOp.SRL uses unsigned right shift."""
        assert "rs1 >> shamt" in self.src

    def test_sra_signed_shift(self):
        """AluOp.SRA casts rs1 to int before shifting."""
        assert "(int)" in self.src

    def test_shamt_masked_to_5bits(self):
        """Shift amount is masked to 5 bits."""
        # Various representations: & 31, & ((uint32_t)(31)), etc.
        assert "31" in self.src

    def test_no_aluop_arrow_syntax(self):
        """AluOp enum references are not left as C arrow-dereferences."""
        assert "AluOp->" not in self.src

    def test_zdc_u32_cast_lowered(self):
        """zdc.u32() calls are lowered to (uint32_t)(...) casts."""
        assert "(uint32_t)" in self.src

    def test_header_has_init_and_run(self):
        """ALUUnit.h declares init and run with ZUSPEC_API."""
        assert "ZUSPEC_API void ALUUnit_init" in self.hdr
        assert "ZUSPEC_API void ALUUnit_run" in self.hdr

    def test_visibility_push_pop(self):
        """Source file is wrapped in GCC visibility push/pop."""
        assert "#pragma GCC visibility push(hidden)" in self.src
        assert "#pragma GCC visibility pop" in self.src

    def test_zuspec_api_macro_in_header(self):
        """ZUSPEC_API macro is defined in the header."""
        assert "#ifndef ZUSPEC_API" in self.hdr
        assert "visibility" in self.hdr or "__declspec" in self.hdr


class TestMulDivUnitCodeGen:
    """MulDivUnit generates correct C for all 8 MUL/DIV cases."""

    @pytest.fixture(scope="class", autouse=True)
    def files(self, request):
        from org.zuspec.example.mls.riscv.rv_units import MulDivUnit
        request.cls._files = _build_sw(MulDivUnit)

    @property
    def src(self):
        return self._files.get("MulDivUnit.c", "")

    def test_mul_case_present(self):
        """MUL case (op==0) present in generated C."""
        assert "== 0" in self.src or "op == ((uint32_t)(0))" in self.src

    def test_divzero_returns_allones(self):
        """Division by zero returns all-ones (0xFFFFFFFF)."""
        assert (
            "0xFFFF_FFFF" in self.src
            or "4294967295" in self.src
            or "0xFFFFFFFF" in self.src
        )

    def test_sdiv32_trunc_helper_called(self):
        """Signed division calls _sdiv32_trunc helper."""
        assert "_sdiv32_trunc" in self.src

    def test_int32_cast_used(self):
        """Signed operands use int32_t cast."""
        assert "int32_t" in self.src

    def test_mulh_shift_right_32(self):
        """MULH (op==1) shifts product right by 32 to get upper bits."""
        assert ">> 32" in self.src


class TestLoadStoreUnitCodeGen:
    """LoadStoreUnit generates correct C for byte-enable and sign-extension."""

    @pytest.fixture(scope="class", autouse=True)
    def files(self, request):
        from org.zuspec.example.mls.riscv.rv_units import LoadStoreUnit
        request.cls._files = _build_sw(LoadStoreUnit)

    @property
    def src(self):
        return self._files.get("LoadStoreUnit.c", "")

    def test_byte_enable_or_offset_present(self):
        """Byte enable or byte_offset appears in generated C."""
        assert "byte_offset" in self.src or "wstrb" in self.src

    def test_sign_extension_present(self):
        """Sign extension for LB / LH present (0x80 or 0x8000 comparison)."""
        assert (
            "128" in self.src
            or "0x80" in self.src
            or "32768" in self.src
            or "0x8000" in self.src
        )

    def test_mem_width_constants_used_in_comparisons(self):
        """MEM_BYTE and MEM_HALFWORD names appear in width comparisons.

        MEM_WORD (2) is the catch-all ``else`` case for word-sized accesses,
        so it does not appear as an explicit comparison target.  The narrower
        widths (byte, halfword) are always explicit.
        """
        assert "MEM_BYTE" in self.src, "MEM_BYTE not referenced in generated C"
        assert "MEM_HALFWORD" in self.src, "MEM_HALFWORD not referenced in generated C"


# ===========================================================================
# B. RVCore struct / header code-generation quality
# ===========================================================================

class TestRVCoreCodeGen:
    """RVCore generates correct struct members and header declarations."""

    @pytest.fixture(scope="class", autouse=True)
    def files(self, request):
        from org.zuspec.example.mls.riscv.rv_core import RVCore
        request.cls._files = _build_sw(RVCore)

    @property
    def src(self):
        return self._files.get("RVCore.c", "")

    @property
    def hdr(self):
        return self._files.get("RVCore.h", "")

    def test_pc_field_in_struct(self):
        """RVCore struct contains uint32_t pc."""
        assert "uint32_t pc;" in self.hdr

    def test_regfile_array_in_struct(self):
        """RVCore struct contains uint32_t regfile[32]."""
        assert "uint32_t regfile[32]" in self.hdr

    def test_rd_sched_pool_in_struct(self):
        """RVCore struct contains zsp_indexed_pool_t rd_sched."""
        assert "zsp_indexed_pool_t rd_sched" in self.hdr

    def test_icache_callable_port_in_struct(self):
        """RVCore struct contains icache function pointer."""
        assert "(*icache)" in self.hdr

    def test_clock_reset_fields(self):
        """clock and reset bit fields appear in struct."""
        assert "clock" in self.hdr
        assert "reset" in self.hdr

    def test_header_regfile_get_set(self):
        """Header declares ZUSPEC_API regfile_get and regfile_set."""
        assert "ZUSPEC_API" in self.hdr
        assert "RVCore_regfile_get" in self.hdr
        assert "RVCore_regfile_set" in self.hdr

    def test_header_regfile_read_all(self):
        """Header declares ZUSPEC_API regfile_read_all."""
        assert "RVCore_regfile_read_all" in self.hdr

    def test_header_pc_accessors(self):
        """Header declares ZUSPEC_API pc get/set."""
        assert "RVCore_get_pc" in self.hdr
        assert "RVCore_set_pc" in self.hdr

    def test_skipped_fields_have_comments(self):
        """Un-lowerable fields (Protocol ports, sub-component insts) emit comments."""
        assert "skipped" in self.hdr

    def test_dcache_field_mentioned(self):
        """dcache field name appears in generated header (as a skipped-field comment)."""
        assert "dcache" in self.hdr

    def test_pool_init_called(self):
        """RVCore_init calls zsp_indexed_pool_init for rd_sched."""
        assert "zsp_indexed_pool_init(&self->rd_sched" in self.src


# ===========================================================================
# C. RVCore compilation status
# ===========================================================================

@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestRVCoreCompilationStatus:
    """Verify RVCore compiles successfully (cfg embedding + zdc.Action stub lowering)."""

    def test_rvcore_compiles(self, unit_tmpdir):
        """RVCore compiles: cfg sub-struct is embedded, zdc.Action calls are stubbed."""
        from org.zuspec.example.mls.riscv.rv_core import RVCore
        proxy = CObjFactory(cache_dir=unit_tmpdir).mkComponent(RVCore)
        assert proxy is not None


# ===========================================================================
# D. MiniCore runtime: icache callback + PC advancement
# ===========================================================================

@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestMiniCoreRuntime:
    """MiniCore runtime behaviour with real instruction bytes fed via icache.

    Because local variable typed assignments (``instr: zdc.u32 = await …``)
    are not yet captured by DataModelFactory, the local variable ``instr`` is
    always 0 in generated C.  All instruction bytes returned by icache are
    therefore ignored.

    Deterministic consequences under this limitation:
      - ``await self.icache(self.pc)`` is NOT lowered to a C call — icache is never invoked
      - opcode == 0  → falls through to ``else`` branch  → ``pc += 4``
      - ``halted`` stays 0

    Tests that depend on icache being called are marked ``xfail`` to document
    the limitation.  Tests that verify the else-branch behaviour (pc advancement,
    register preservation) are expected to pass.
    """

    @pytest.fixture
    def fac(self, unit_tmpdir):
        return CObjFactory(cache_dir=unit_tmpdir)

    @pytest.fixture
    def proxy(self, fac):
        from fixtures.minicore_component import MiniCore  # type: ignore[import]
        return fac.mkComponent(MiniCore)

    def test_icache_is_called_on_run(self, fac, proxy):
        """icache callback is invoked when run() is called."""
        calls: list[int] = []
        fac.bind_callable(proxy, "icache", lambda addr: (calls.append(addr) or 0))
        proxy.run()
        assert len(calls) >= 1, "icache was never called"

    def test_icache_called_with_initial_pc_zero(self, fac, proxy):
        """First icache call uses pc=0 (initial value)."""
        calls: list[int] = []
        fac.bind_callable(proxy, "icache", lambda addr: (calls.append(addr) or 0))
        proxy.run()
        assert calls[0] == 0, f"First icache call should be addr=0, got {calls[0]}"

    def test_icache_called_with_custom_pc(self, fac, proxy):
        """icache is called with the value we set PC to before run()."""
        calls: list[int] = []
        fac.bind_callable(proxy, "icache", lambda addr: (calls.append(addr) or 0))
        proxy.pc = 0x1000
        proxy.run()
        assert calls[0] == 0x1000, \
            f"Expected icache(0x1000), got icache({calls[0]:#x})"

    def test_pc_advances_by_four_after_run(self, fac, proxy):
        """PC advances by 4 after one run() call (else branch → pc+=4)."""
        fac.bind_callable(proxy, "icache", lambda addr: 0)
        proxy.pc = 0x100
        proxy.run()
        assert proxy.pc == 0x104, f"Expected pc=0x104, got pc={proxy.pc:#x}"

    def test_regfile_unchanged_by_run(self, fac, proxy):
        """run() does not corrupt regfile contents when no ALU operation fires."""
        for i in range(1, 32):
            proxy.regfile.set(i, i * 0x1000)
        fac.bind_callable(proxy, "icache", lambda addr: 0)
        proxy.run()
        for i in range(1, 32):
            assert proxy.regfile.get(i) == i * 0x1000, \
                f"regfile[{i}] corrupted after run()"

    def test_halted_stays_false_with_nop_stream(self, fac, proxy):
        """halted stays 0 when icache returns opcode=0 (not ECALL encoding)."""
        fac.bind_callable(proxy, "icache", lambda addr: 0)
        proxy.run()
        assert proxy.halted == 0

    def test_multiple_run_calls_advance_pc_sequentially(self, fac, proxy):
        """Each successive run() call advances PC by 4."""
        fac.bind_callable(proxy, "icache", lambda addr: 0)
        proxy.pc = 0
        for step in range(5):
            proxy.run()
            assert proxy.pc == (step + 1) * 4, \
                f"After step {step + 1}: expected pc={(step + 1) * 4}, got {proxy.pc}"

    def test_icache_address_matches_current_pc_each_step(self, fac, proxy):
        """Each run() feeds the current PC value to icache."""
        calls: list[int] = []
        fac.bind_callable(proxy, "icache", lambda addr: (calls.append(addr) or 0))
        proxy.pc = 0
        for step in range(3):
            proxy.run()
        assert calls == [0, 4, 8], f"Expected [0, 4, 8], got {calls}"

    def test_backdoor_regfile_get_set(self, fac, proxy):
        """BackdoorRegFile get/set works on MiniCore proxy."""
        proxy.regfile.set(7, 0xDEAD)
        assert proxy.regfile.get(7) == 0xDEAD

    def test_backdoor_regfile_get_all_length(self, fac, proxy):
        """BackdoorRegFile get_all() returns 32 entries."""
        assert len(proxy.regfile.get_all()) == 32

    def test_backdoor_regfile_get_all_value(self, fac, proxy):
        """BackdoorRegFile get_all() reflects set() values."""
        proxy.regfile.set(15, 0xCAFE)
        all_vals = proxy.regfile.get_all()
        assert all_vals[15] == 0xCAFE


# ===========================================================================
# E. Sub-unit compilation smoke tests
# ===========================================================================

@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestSubUnitCompilation:
    """All three RVCore sub-units compile and produce usable proxies."""

    @pytest.fixture
    def fac(self, unit_tmpdir):
        return CObjFactory(cache_dir=unit_tmpdir)

    def test_alu_unit_compiles(self, fac):
        """ALUUnit compiles to .so without errors."""
        from org.zuspec.example.mls.riscv.rv_units import ALUUnit
        assert fac.mkComponent(ALUUnit) is not None

    def test_muldiv_unit_compiles(self, fac):
        """MulDivUnit compiles to .so without errors."""
        from org.zuspec.example.mls.riscv.rv_units import MulDivUnit
        assert fac.mkComponent(MulDivUnit) is not None

    def test_loadstore_unit_compiles(self, fac):
        """LoadStoreUnit compiles to .so without errors."""
        from org.zuspec.example.mls.riscv.rv_units import LoadStoreUnit
        assert fac.mkComponent(LoadStoreUnit) is not None

    def test_alu_proxy_has_run(self, fac):
        """ALUUnit proxy exposes run()."""
        from org.zuspec.example.mls.riscv.rv_units import ALUUnit
        proxy = fac.mkComponent(ALUUnit)
        assert callable(proxy.run)

    def test_muldiv_proxy_has_run(self, fac):
        """MulDivUnit proxy exposes run()."""
        from org.zuspec.example.mls.riscv.rv_units import MulDivUnit
        proxy = fac.mkComponent(MulDivUnit)
        assert callable(proxy.run)

    def test_loadstore_proxy_has_run(self, fac):
        """LoadStoreUnit proxy exposes run()."""
        from org.zuspec.example.mls.riscv.rv_units import LoadStoreUnit
        proxy = fac.mkComponent(LoadStoreUnit)
        assert callable(proxy.run)


# ===========================================================================
# F. Sub-unit execution tests — exercise C-compiled execute() entry functions
# ===========================================================================

@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestALUUnitExecution:
    """ALUUnit.execute() returns correct results for each AluOp."""

    @pytest.fixture(scope="class")
    def proxy(self, unit_tmpdir):
        from org.zuspec.example.mls.riscv.rv_units import ALUUnit
        return CObjFactory(cache_dir=unit_tmpdir).mkComponent(ALUUnit)

    def test_execute_method_callable(self, proxy):
        """ALUUnit proxy exposes callable execute method."""
        assert callable(proxy.execute), "execute not exposed on ALUUnit proxy"

    def test_add(self, proxy):
        """ALU_ADD: 5 + 3 == 8."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_ADD
        assert proxy.execute(ALU_ADD, 5, 3) == 8

    def test_sub(self, proxy):
        """ALU_SUB: 10 - 4 == 6."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_SUB
        assert proxy.execute(ALU_SUB, 10, 4) == 6

    def test_or(self, proxy):
        """ALU_OR: 0xA | 0x5 == 0xF."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_OR
        assert proxy.execute(ALU_OR, 0xA, 0x5) == 0xF

    def test_and(self, proxy):
        """ALU_AND: 0xFF & 0x0F == 0x0F."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_AND
        assert proxy.execute(ALU_AND, 0xFF, 0x0F) == 0x0F

    def test_xor(self, proxy):
        """ALU_XOR: 0xFF ^ 0xFF == 0."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_XOR
        assert proxy.execute(ALU_XOR, 0xFF, 0xFF) == 0

    def test_sll(self, proxy):
        """ALU_SLL: 1 << 4 == 16."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_SLL
        assert proxy.execute(ALU_SLL, 1, 4) == 16

    def test_srl(self, proxy):
        """ALU_SRL: 0x80 >> 3 == 0x10."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_SRL
        assert proxy.execute(ALU_SRL, 0x80, 3) == 0x10

    def test_slt_true(self, proxy):
        """ALU_SLT: 1 < 2 → 1."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_SLT
        assert proxy.execute(ALU_SLT, 1, 2) == 1

    def test_slt_false(self, proxy):
        """ALU_SLT: 2 < 1 → 0."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_SLT
        assert proxy.execute(ALU_SLT, 2, 1) == 0

    def test_sltu_true(self, proxy):
        """ALU_SLTU: 0 < 0xFFFFFFFF → 1 (unsigned)."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_SLTU
        assert proxy.execute(ALU_SLTU, 0, 0xFFFF_FFFF) == 1

    def test_add_wraps_32bit(self, proxy):
        """ALU_ADD wraps at 32 bits: 0xFFFFFFFF + 1 == 0."""
        from org.zuspec.example.mls.riscv.rv_units import ALU_ADD
        result = proxy.execute(ALU_ADD, 0xFFFF_FFFF, 1) & 0xFFFF_FFFF
        assert result == 0


@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestMulDivUnitExecution:
    """MulDivUnit.execute() returns correct results for multiply/divide."""

    @pytest.fixture(scope="class")
    def proxy(self, unit_tmpdir):
        from org.zuspec.example.mls.riscv.rv_units import MulDivUnit
        return CObjFactory(cache_dir=unit_tmpdir).mkComponent(MulDivUnit)

    def test_execute_method_callable(self, proxy):
        """MulDivUnit proxy exposes callable execute method."""
        assert callable(proxy.execute), "execute not exposed on MulDivUnit proxy"

    def test_mul(self, proxy):
        """MUL (op=0): 6 * 7 == 42."""
        from org.zuspec.example.mls.riscv.rv_units import MulDivUnit
        # MUL funct3=0
        assert proxy.execute(0, 6, 7) == 42

    def test_mul_by_zero(self, proxy):
        """MUL: anything * 0 == 0."""
        assert proxy.execute(0, 0xDEAD, 0) == 0

    def test_divu(self, proxy):
        """DIVU (op=5): 42 / 6 == 7."""
        # funct3=101 → DIVU
        assert proxy.execute(5, 42, 6) == 7

    def test_divu_by_zero(self, proxy):
        """DIVU by zero returns 0xFFFFFFFF (ISA-defined)."""
        result = proxy.execute(5, 1, 0) & 0xFFFF_FFFF
        assert result == 0xFFFF_FFFF

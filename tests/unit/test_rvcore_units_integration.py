"""Integration tests for RVCore sub-units: ALUUnit, MulDivUnit, LoadStoreUnit.

These tests verify that the three execution units from rv_units.py compile
cleanly via CObjFactory and that generated proxies expose the expected API.
"""
import sys
import os
import tempfile
from pathlib import Path

import pytest

# Add example src to path
_PROJ_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(_PROJ_ROOT / "src"))
sys.path.insert(0, str(_PROJ_ROOT / "packages" / "zuspec-dataclasses" / "src"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmpdir_path():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _make_factory(tmpdir_path):
    from zuspec.be.sw.co_obj_factory import CObjFactory
    return CObjFactory(cache_dir=tmpdir_path)


# ---------------------------------------------------------------------------
# ALUUnit tests
# ---------------------------------------------------------------------------

class TestALUUnitCompilation:
    """ALUUnit compiles without errors and proxy has expected API."""

    @pytest.fixture(scope="class")
    def alu_proxy(self, tmpdir_path):
        from org.zuspec.example.mls.riscv.rv_units import ALUUnit
        from zuspec.be.sw.co_obj_factory import CObjFactory
        fac = CObjFactory(cache_dir=tmpdir_path)
        return fac.mkComponent(ALUUnit)

    def test_alu_compiles(self, alu_proxy):
        """ALUUnit compiles and mkComponent succeeds."""
        assert alu_proxy is not None

    def test_alu_proxy_has_run(self, alu_proxy):
        """ALUUnit proxy exposes run() method."""
        assert callable(getattr(alu_proxy, "run", None))


# ---------------------------------------------------------------------------
# MulDivUnit tests
# ---------------------------------------------------------------------------

class TestMulDivUnitCompilation:
    """MulDivUnit compiles without errors."""

    @pytest.fixture(scope="class")
    def muldiv_proxy(self, tmpdir_path):
        from org.zuspec.example.mls.riscv.rv_units import MulDivUnit
        from zuspec.be.sw.co_obj_factory import CObjFactory
        fac = CObjFactory(cache_dir=tmpdir_path)
        return fac.mkComponent(MulDivUnit)

    def test_muldiv_compiles(self, muldiv_proxy):
        """MulDivUnit compiles and mkComponent succeeds."""
        assert muldiv_proxy is not None

    def test_muldiv_proxy_has_run(self, muldiv_proxy):
        """MulDivUnit proxy exposes run() method."""
        assert callable(getattr(muldiv_proxy, "run", None))


# ---------------------------------------------------------------------------
# LoadStoreUnit tests
# ---------------------------------------------------------------------------

class TestLoadStoreUnitCompilation:
    """LoadStoreUnit compiles without errors."""

    @pytest.fixture(scope="class")
    def lsu_proxy(self, tmpdir_path):
        from org.zuspec.example.mls.riscv.rv_units import LoadStoreUnit
        from zuspec.be.sw.co_obj_factory import CObjFactory
        fac = CObjFactory(cache_dir=tmpdir_path)
        return fac.mkComponent(LoadStoreUnit)

    def test_lsu_compiles(self, lsu_proxy):
        """LoadStoreUnit compiles and mkComponent succeeds."""
        assert lsu_proxy is not None

    def test_lsu_proxy_has_run(self, lsu_proxy):
        """LoadStoreUnit proxy exposes run() method."""
        assert callable(getattr(lsu_proxy, "run", None))


# ---------------------------------------------------------------------------
# Generated C code quality checks
# ---------------------------------------------------------------------------

class TestALUCodeGenQuality:
    """Spot-check quality of generated ALUUnit C code."""

    @pytest.fixture(scope="class")
    def alu_source(self, tmpdir_path):
        """Return the generated ALUUnit.c source."""
        from org.zuspec.example.mls.riscv.rv_units import ALUUnit
        from zuspec.be.sw.co_obj_factory import CObjFactory
        from zuspec.dataclasses import DataModelFactory
        from zuspec.be.sw.pipeline import SwPassManager
        import sys as _sys

        ir_ctx = DataModelFactory().build(ALUUnit)
        py_globals = getattr(_sys.modules.get(ALUUnit.__module__), "__dict__", {}) or {}
        sw_ctx = SwPassManager().run(ir_ctx, py_globals=py_globals)

        for fname, content in sw_ctx.output_files:
            if fname == "ALUUnit.c":
                return content
        return ""

    def test_enum_values_resolved(self, alu_source):
        """AluOp enum values should be integers (0, 1, …) not 'AluOp->ADD'."""
        assert "AluOp->ADD" not in alu_source
        assert "AluOp->SUB" not in alu_source
        # Should contain integer comparisons
        assert "op == 0" in alu_source or "op == 1" in alu_source

    def test_shamt_declared(self, alu_source):
        """shamt local variable should be declared."""
        assert "uint32_t shamt = 0;" in alu_source

    def test_s32_cast(self, alu_source):
        """_s32() calls should be lowered to C casts."""
        assert "_s32(" not in alu_source
        assert "(int32_t)" in alu_source

    def test_zdc_u32_cast(self, alu_source):
        """zdc.u32() calls should be lowered to C casts."""
        assert "zdc->u32(" not in alu_source
        assert "(uint32_t)" in alu_source

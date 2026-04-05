"""Phase 5 integration tests for MiniCore — a minimal RISC-V-like component.

These tests verify that MiniCore (IndexedRegFile + IndexedPool + callable port +
process) can be compiled to C, loaded, and partially executed through CObjFactory.

All execution tests bind the ``icache`` callable port to return 0 (NOP-like).
With opcode=0, neither ADDI(0x13) nor ECALL(0x73) matches, so the "else"
branch fires: ``self->pc = (self->pc + 4) & 0xFFFFFFFF``.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

try:
    from zuspec.be.sw.co_obj_factory import CObjFactory
    from zuspec.be.sw.co_obj_factory import _RegFileProxy
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False


@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestMiniCoreCompilation:
    """Verify MiniCore compiles and all proxy attributes are accessible."""

    def _make_proxy(self, tmpdir: str):
        from fixtures.minicore_component import MiniCore  # type: ignore[import]
        fac = CObjFactory(cache_dir=Path(tmpdir))
        return fac.mkComponent(MiniCore)

    def test_minicore_compiles(self):
        """MiniCore with IndexedRegFile + IndexedPool + port compiles to .so."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            assert proxy is not None

    def test_initial_pc_is_zero(self):
        """pc field starts at 0 after init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            assert proxy.pc == 0

    def test_initial_halted_is_false(self):
        """halted flag starts as 0 (False) after init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            assert proxy.halted == 0

    def test_regfile_proxy_type(self):
        """regfile attribute returns a _RegFileProxy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            assert isinstance(proxy.regfile, _RegFileProxy)

    def test_regfile_initial_zero(self):
        """All 32 integer registers start at 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            for i in range(32):
                assert proxy.regfile[i] == 0, f"regfile[{i}] != 0"

    def test_regfile_write_read_roundtrip(self):
        """Write to a register then read it back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            proxy.regfile[5] = 0xDEADBEEF
            assert proxy.regfile[5] == 0xDEADBEEF

    def test_regfile_all_registers_independent(self):
        """Writes to different registers are independent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            for i in range(1, 32):
                proxy.regfile[i] = i * 4
            for i in range(1, 32):
                assert proxy.regfile[i] == i * 4

    def test_pc_field_writable(self):
        """pc field can be written and read back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            proxy.pc = 0x1000
            assert proxy.pc == 0x1000

    def test_halted_field_writable(self):
        """halted field can be set to 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proxy = self._make_proxy(tmpdir)
            proxy.halted = 1
            assert proxy.halted == 1

    def test_icache_port_bindable(self):
        """icache port can be bound to a Python callable without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from zuspec.be.sw.co_obj_factory import CObjFactory
            from fixtures.minicore_component import MiniCore  # type: ignore[import]
            calls: list = []

            def my_icache(addr: int) -> int:
                calls.append(addr)
                return 0  # NOP-like

            fac = CObjFactory(cache_dir=Path(tmpdir))
            proxy = fac.mkComponent(MiniCore)
            fac.bind_callable(proxy, "icache", my_icache)
            # Binding should not crash; callable should be reachable


@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestMiniCoreExecution:
    """Verify that run() actually executes the generated process body."""

    def _make_fac_proxy(self, tmpdir: str):
        from fixtures.minicore_component import MiniCore  # type: ignore[import]
        fac = CObjFactory(cache_dir=Path(tmpdir))
        proxy = fac.mkComponent(MiniCore)
        # Always bind icache to return 0 (NOP-like: opcode=0 → else branch → pc+=4)
        fac.bind_callable(proxy, "icache", lambda addr: 0)
        return fac, proxy

    def test_run_does_not_crash(self):
        """Calling run() completes without exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, proxy = self._make_fac_proxy(tmpdir)
            proxy.run()  # must not raise

    def test_run_advances_pc(self):
        """After run(), pc is 4 (icache returns 0 → opcode=0 → else → pc+=4)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, proxy = self._make_fac_proxy(tmpdir)
            assert proxy.pc == 0
            proxy.run()
            assert proxy.pc == 4

    def test_run_does_not_set_halted(self):
        """After run() with zero opcode, halted remains 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, proxy = self._make_fac_proxy(tmpdir)
            proxy.run()
            assert proxy.halted == 0

    def test_pc_continues_from_set_value(self):
        """If pc is pre-loaded to 0x100, after run() it becomes 0x104."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, proxy = self._make_fac_proxy(tmpdir)
            proxy.pc = 0x100
            proxy.run()
            assert proxy.pc == 0x104

    def test_multiple_run_calls(self):
        """Calling run() N times advances pc by 4*N."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, proxy = self._make_fac_proxy(tmpdir)
            for i in range(5):
                proxy.run()
                assert proxy.pc == 4 * (i + 1)

    def test_regfile_unmodified_by_run(self):
        """Run with opcode=0 does not modify the register file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, proxy = self._make_fac_proxy(tmpdir)
            proxy.regfile[1] = 42
            proxy.run()
            assert proxy.regfile[1] == 42  # unchanged

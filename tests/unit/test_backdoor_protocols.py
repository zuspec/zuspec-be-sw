"""Tests for BackdoorRegFile and BackdoorMemory Protocols.

Verifies that both the Python-rt implementations (IndexedRegFileRT, MemoryRT)
and the C-backend implementations (_RegFileProxy, future _MemoryProxy) satisfy
the same protocol contracts so test code is backend-agnostic.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import zuspec.dataclasses as zdc
from zuspec.dataclasses import BackdoorRegFile, BackdoorMemory, MemoryRT
from zuspec.dataclasses.rt.indexed_regfile_rt import IndexedRegFileRT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_regfile_rt(depth: int = 32) -> IndexedRegFileRT:
    """Create a Python-rt IndexedRegFile instance."""
    return IndexedRegFileRT(depth=depth, read_ports=2, write_ports=1)


try:
    from zuspec.be.sw.co_obj_factory import CObjFactory, _RegFileProxy, _MemoryProxy
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False


def _make_regfile_proxy(tmpdir: str) -> "_RegFileProxy":
    """Compile MiniCore and return its regfile proxy."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from fixtures.minicore_component import MiniCore  # type: ignore[import]
    fac = CObjFactory(cache_dir=Path(tmpdir))
    proxy = fac.mkComponent(MiniCore)
    return proxy.regfile


# ---------------------------------------------------------------------------
# BackdoorRegFile — Python rt
# ---------------------------------------------------------------------------

class TestBackdoorRegFilePythonRT:
    """BackdoorRegFile protocol contract on IndexedRegFileRT."""

    def test_implements_protocol(self):
        """IndexedRegFileRT satisfies BackdoorRegFile statically."""
        rf = _make_regfile_rt()
        # Runtime isinstance check via typing.runtime_checkable is not
        # available on Protocol; verify duck-typing instead.
        assert hasattr(rf, "get")
        assert hasattr(rf, "set")
        assert hasattr(rf, "get_all")

    def test_initial_zero(self):
        """All registers start at 0."""
        rf = _make_regfile_rt()
        for i in range(32):
            assert rf.get(i) == 0, f"register {i} != 0"

    def test_set_get_roundtrip(self):
        """set then get returns same value."""
        rf = _make_regfile_rt()
        rf.set(5, 0xDEAD_BEEF)
        assert rf.get(5) == 0xDEAD_BEEF

    def test_registers_independent(self):
        """Writes to different registers don't interfere."""
        rf = _make_regfile_rt()
        for i in range(1, 32):
            rf.set(i, i * 7)
        for i in range(1, 32):
            assert rf.get(i) == i * 7

    def test_get_all_length(self):
        """get_all() returns a list of length == depth."""
        rf = _make_regfile_rt()
        result = rf.get_all()
        assert isinstance(result, list)
        assert len(result) == 32

    def test_get_all_reflects_writes(self):
        """get_all() values match individual get() calls after writes."""
        rf = _make_regfile_rt()
        for i in range(1, 32):
            rf.set(i, i * 3)
        all_vals = rf.get_all()
        for i in range(1, 32):
            assert all_vals[i] == rf.get(i)


# ---------------------------------------------------------------------------
# BackdoorRegFile — C backend
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestBackdoorRegFileCBackend:
    """BackdoorRegFile protocol contract on _RegFileProxy (C backend)."""

    def test_implements_protocol_methods(self):
        """_RegFileProxy has get, set, get_all."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = _make_regfile_proxy(tmpdir)
            assert hasattr(rf, "get")
            assert hasattr(rf, "set")
            assert hasattr(rf, "get_all")

    def test_initial_zero(self):
        """All registers start at 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = _make_regfile_proxy(tmpdir)
            for i in range(32):
                assert rf.get(i) == 0, f"register {i} != 0"

    def test_set_get_roundtrip(self):
        """set then get returns same value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = _make_regfile_proxy(tmpdir)
            rf.set(5, 0xDEAD_BEEF)
            assert rf.get(5) == 0xDEAD_BEEF

    def test_registers_independent(self):
        """Writes to different registers don't interfere."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = _make_regfile_proxy(tmpdir)
            for i in range(1, 32):
                rf.set(i, i * 7)
            for i in range(1, 32):
                assert rf.get(i) == i * 7

    def test_get_all_length(self):
        """get_all() returns a list of length 32."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = _make_regfile_proxy(tmpdir)
            result = rf.get_all()
            assert isinstance(result, list)
            assert len(result) == 32

    def test_get_all_reflects_writes(self):
        """get_all() matches individual get() after writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = _make_regfile_proxy(tmpdir)
            for i in range(1, 32):
                rf.set(i, i * 3)
            all_vals = rf.get_all()
            for i in range(1, 32):
                assert all_vals[i] == rf.get(i)

    def test_subscript_still_works(self):
        """Legacy subscript syntax delegates to get/set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rf = _make_regfile_proxy(tmpdir)
            rf[10] = 42
            assert rf[10] == 42
            assert rf.get(10) == 42


# ---------------------------------------------------------------------------
# Protocol parity: same contract on both backends
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestBackdoorRegFileProtocolParity:
    """Identical test body runs against both rt and C proxy."""

    @staticmethod
    def _run_parity_checks(rf: BackdoorRegFile) -> None:
        # Initial state
        for i in range(32):
            assert rf.get(i) == 0
        # Write some values
        rf.set(1, 0x1111)
        rf.set(15, 0xABCD)
        rf.set(31, 0xFFFF_FFFF)
        # Verify
        assert rf.get(1) == 0x1111
        assert rf.get(15) == 0xABCD
        assert rf.get(31) == 0xFFFF_FFFF
        # get_all consistency
        all_vals = rf.get_all()
        assert all_vals[1] == 0x1111
        assert all_vals[15] == 0xABCD
        assert all_vals[31] == 0xFFFF_FFFF

    def test_python_rt_parity(self):
        """Python rt passes protocol parity checks."""
        self._run_parity_checks(_make_regfile_rt())

    def test_c_backend_parity(self):
        """C backend passes protocol parity checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._run_parity_checks(_make_regfile_proxy(tmpdir))


# ---------------------------------------------------------------------------
# BackdoorMemory — MemoryRT
# ---------------------------------------------------------------------------

class TestBackdoorMemoryRT:
    """BackdoorMemory protocol contract on MemoryRT."""

    def test_implements_protocol_methods(self):
        """MemoryRT has read_bytes and write_bytes."""
        mem = MemoryRT(_size=1024)
        assert hasattr(mem, "read_bytes")
        assert hasattr(mem, "write_bytes")

    def test_initial_zero(self):
        """Freshly created memory reads as all zeros."""
        mem = MemoryRT(_size=1024)
        data = mem.read_bytes(0, 16)
        assert data == bytes(16)

    def test_write_bytes_read_bytes_roundtrip(self):
        """Bytes written can be read back intact."""
        mem = MemoryRT(_size=1024)
        payload = bytes([0x93, 0x00, 0x00, 0x00])  # ADDI x1, x0, 0 (RV32I)
        mem.write_bytes(0x100, payload)
        result = mem.read_bytes(0x100, 4)
        assert result == payload

    def test_write_read_32bit_word(self):
        """A 32-bit little-endian word survives write/read roundtrip."""
        mem = MemoryRT(_size=1024)
        val = 0xDEAD_BEEF
        mem.write_bytes(0x10, val.to_bytes(4, "little"))
        back = int.from_bytes(mem.read_bytes(0x10, 4), "little")
        assert back == val

    def test_partial_write_does_not_corrupt_neighbours(self):
        """Writing 1 byte doesn't corrupt adjacent bytes in same element."""
        mem = MemoryRT(_size=1024)
        # Write a full word first
        mem.write_bytes(0, (0x12345678).to_bytes(4, "little"))
        # Overwrite byte 1
        mem.write_bytes(1, bytes([0xAB]))
        result = int.from_bytes(mem.read_bytes(0, 4), "little")
        # byte 0 unchanged (0x78), byte 1 = 0xAB, bytes 2-3 unchanged
        assert result == 0x1234_AB78

    def test_multi_element_read(self):
        """Reading across element boundaries works correctly."""
        mem = MemoryRT(_size=1024)
        # Write to elements 0 and 1
        mem.write_bytes(0, bytes([0x01, 0x02, 0x03, 0x04]))
        mem.write_bytes(4, bytes([0x05, 0x06, 0x07, 0x08]))
        result = mem.read_bytes(2, 4)  # crosses element boundary
        assert result == bytes([0x03, 0x04, 0x05, 0x06])

    def test_instruction_sequence(self):
        """Simulate loading a short RISC-V instruction sequence."""
        mem = MemoryRT(_size=4096)
        # addi x1, x0, 1   (0x00100093)
        # addi x2, x0, 2   (0x00200113)
        # ecall             (0x00000073)
        instrs = [0x00100093, 0x00200113, 0x00000073]
        for i, instr in enumerate(instrs):
            mem.write_bytes(i * 4, instr.to_bytes(4, "little"))
        for i, expected in enumerate(instrs):
            word = int.from_bytes(mem.read_bytes(i * 4, 4), "little")
            assert word == expected, f"instr[{i}] mismatch"

    def test_element_read_and_read_bytes_consistent(self):
        """MemoryRT.read(elem_idx) is consistent with read_bytes byte-level view."""
        mem = MemoryRT(_size=1024)
        # Write via element API
        mem.write(3, 0xCAFE_BABE)
        # Read back via byte API at byte offset 3*4 = 12
        raw = mem.read_bytes(12, 4)
        from_bytes = int.from_bytes(raw, "little")
        assert from_bytes == 0xCAFE_BABE

    def test_element_write_and_read_bytes_consistent(self):
        """write_bytes and read() are consistent."""
        mem = MemoryRT(_size=1024)
        # Write via byte API at element 5 (byte offset 20)
        mem.write_bytes(20, (0xDEAD_BEEF).to_bytes(4, "little"))
        # Read back via element API
        assert mem.read(5) == 0xDEAD_BEEF


# ---------------------------------------------------------------------------
# BackdoorMemory — C backend
# ---------------------------------------------------------------------------

def _make_memory_proxy(tmpdir: str) -> "_MemoryProxy":
    """Compile MemComp and return its mem proxy."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from fixtures.simple_components import MemComp  # type: ignore[import]
    fac = CObjFactory(cache_dir=Path(tmpdir))
    proxy = fac.mkComponent(MemComp)
    return proxy.mem


@pytest.mark.skipif(not HAS_BACKEND, reason="be-sw backend not available")
class TestBackdoorMemoryCBackend:
    """BackdoorMemory protocol contract on _MemoryProxy (C backend)."""

    def test_implements_protocol_methods(self):
        """_MemoryProxy has read, write, read_bytes, write_bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = _make_memory_proxy(tmpdir)
        assert hasattr(mem, "read")
        assert hasattr(mem, "write")
        assert hasattr(mem, "read_bytes")
        assert hasattr(mem, "write_bytes")

    def test_initial_zero(self):
        """Freshly initialised memory reads as all zeros."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = _make_memory_proxy(tmpdir)
            assert mem.read(0) == 0
            assert mem.read(1023) == 0
            assert mem.read_bytes(0, 16) == bytes(16)

    def test_write_read_roundtrip(self):
        """Element written can be read back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = _make_memory_proxy(tmpdir)
            mem.write(10, 0xDEAD_BEEF)
            assert mem.read(10) == 0xDEAD_BEEF

    def test_elements_independent(self):
        """Writes to different elements don't interfere."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = _make_memory_proxy(tmpdir)
            for i in range(16):
                mem.write(i, i * 0x11111111)
            for i in range(16):
                assert mem.read(i) == i * 0x11111111

    def test_write_bytes_read_bytes_roundtrip(self):
        """Bytes written can be read back intact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = _make_memory_proxy(tmpdir)
            payload = bytes([0x93, 0x00, 0x00, 0x00])
            mem.write_bytes(0x100, payload)
            assert mem.read_bytes(0x100, 4) == payload

    def test_element_and_bytes_consistent(self):
        """Element write and read_bytes are byte-consistent (little-endian)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = _make_memory_proxy(tmpdir)
            mem.write(3, 0xCAFE_BABE)
            raw = mem.read_bytes(12, 4)  # elem 3 → byte offset 12
            assert int.from_bytes(raw, "little") == 0xCAFE_BABE

    def test_instruction_sequence(self):
        """Simulate loading a short RISC-V instruction sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = _make_memory_proxy(tmpdir)
            instrs = [0x00100093, 0x00200113, 0x00000073]
            for i, instr in enumerate(instrs):
                mem.write_bytes(i * 4, instr.to_bytes(4, "little"))
            for i, expected in enumerate(instrs):
                word = int.from_bytes(mem.read_bytes(i * 4, 4), "little")
                assert word == expected, f"instr[{i}] mismatch"


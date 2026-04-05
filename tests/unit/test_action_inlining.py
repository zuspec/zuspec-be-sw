"""Tests for zdc.Action inlining in the C code generator.

Verifies that ``await ActionCls(kwargs)(comp=self)`` is:
  1. Detected and inlined by DataModelFactory (no more ``0 /* zdc.Action call */``).
  2. The action struct appears in the coroutine locals typedef.
  3. The generated C compiles without errors.
"""
from __future__ import annotations

import os
import typing
import tempfile

import pytest
import zuspec.dataclasses as zdc

from zuspec.be.sw import CGenerator


# ---------------------------------------------------------------------------
# Fixtures — must be at module level so inspect.getsource() works
# ---------------------------------------------------------------------------

@zdc.dataclass
class Decode(zdc.Action['SimpleCore']):
    """Minimal decode action: fetch instruction word via icache."""
    pc_in: zdc.u32 = zdc.input()
    insn32: zdc.u32 = zdc.output()

    async def body(self):
        self.insn32 = await self.comp.icache(self.pc_in)


@zdc.dataclass
class SimpleCore(zdc.Component):
    """Component that inlines Decode in its run() process."""
    icache: typing.Callable[[int], typing.Awaitable[int]] = zdc.port()
    pc: zdc.u32 = zdc.field(default=0)
    last_insn: zdc.u32 = zdc.field(default=0)

    @zdc.process
    async def run(self):
        fn: zdc.u32 = await Decode(pc_in=self.pc)(comp=self)
        self.last_insn = fn.insn32


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestActionInlining:
    """Test that action inlining generates correct C."""

    def _generate(self, tmpdir: str):
        dm_ctxt = zdc.DataModelFactory().build(SimpleCore)
        gen = CGenerator(output_dir=tmpdir)
        return gen.generate(dm_ctxt), dm_ctxt

    def test_no_action_stub_in_generated_c(self, tmp_path):
        """The generated .c file must not contain the old action placeholder."""
        sources, _ = self._generate(str(tmp_path))
        for s in sources:
            if s.suffix == '.c' and s.name != 'main.c':
                content = s.read_text()
                assert "zdc.Action call" not in content, \
                    f"Stale action stub found in {s.name}:\n{content}"

    def test_action_struct_in_locals_typedef(self, tmp_path):
        """Decode_t must appear in the generated source or header."""
        sources, _ = self._generate(str(tmp_path))
        found = False
        for s in sources:
            if s.suffix in ('.h', '.c') and s.name != 'main.c':
                if "Decode_t" in s.read_text():
                    found = True
                    break
        assert found, "Decode_t not found in any generated file"

    def test_action_field_uses_dot_not_arrow(self, tmp_path):
        """Action field access must use '.' not '->' (struct embedded by value)."""
        sources, _ = self._generate(str(tmp_path))
        for s in sources:
            if s.suffix == '.c' and s.name != 'main.c':
                content = s.read_text()
                # Should contain  locals->fn.insn32  not  locals->fn->insn32
                assert "->fn->" not in content, \
                    f"Wrong arrow operator for action field in {s.name}"

    def test_generated_c_compiles(self, tmp_path):
        """The generated C must compile without errors using gcc."""
        pytest.importorskip("subprocess")
        import subprocess

        sources, _ = self._generate(str(tmp_path))

        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        share_dir = os.path.join(repo_root, "src", "zuspec", "be", "sw", "share")
        rt_dir = os.path.join(share_dir, "rt")
        include_dir = os.path.join(share_dir, "include")

        rt_sources = [
            os.path.join(rt_dir, f)
            for f in ["zsp_alloc.c", "zsp_timebase.c", "zsp_list.c",
                      "zsp_map.c", "zsp_object.c", "zsp_component.c"]
            if os.path.exists(os.path.join(rt_dir, f))
        ]

        c_sources = [str(s) for s in sources if s.suffix == '.c']
        exe = str(tmp_path / "test_action")
        cmd = ["gcc", "-g", "-O0",
               f"-I{include_dir}", f"-I{str(tmp_path)}",
               "-o", exe] + c_sources + rt_sources
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, \
            f"Compilation failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

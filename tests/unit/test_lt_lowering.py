"""Tests for P3: LT-mode wait codegen.

Verifies that coroutine wait-points are lowered to ``ZSP_WAIT_PS`` when
``ctxt.tlm_sync_mode`` is set, and to the legacy ``zsp_timebase_wait`` call
when it is not (backward compatibility).
"""
import pytest

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.coroutine import (
    SwCoroutineFrame,
    SwContinuation,
    SwSuspendWait,
)
from zuspec.be.sw.passes.c_emit import CEmitPass, _duration_to_ps_str


# ---------------------------------------------------------------------------
# Unit tests for _duration_to_ps_str
# ---------------------------------------------------------------------------

class TestDurationToPsStr:
    def test_none_returns_zero(self):
        assert _duration_to_ps_str(None) == "0"

    def test_plain_constant(self):
        dur = ir.ExprConstant(value=5000)
        assert _duration_to_ps_str(dur) == "5000"

    def test_ns_call(self):
        dur = ir.ExprCall(
            func=ir.ExprRefUnresolved(name="ns"),
            args=[ir.ExprConstant(value=10)],
        )
        assert _duration_to_ps_str(dur) == "10000"

    def test_us_call(self):
        dur = ir.ExprCall(
            func=ir.ExprRefUnresolved(name="us"),
            args=[ir.ExprConstant(value=1)],
        )
        assert _duration_to_ps_str(dur) == "1000000"

    def test_ms_call(self):
        dur = ir.ExprCall(
            func=ir.ExprRefUnresolved(name="ms"),
            args=[ir.ExprConstant(value=2)],
        )
        assert _duration_to_ps_str(dur) == "2000000000"

    def test_s_call(self):
        dur = ir.ExprCall(
            func=ir.ExprRefUnresolved(name="s"),
            args=[ir.ExprConstant(value=1)],
        )
        assert _duration_to_ps_str(dur) == "1000000000000"

    def test_ps_call(self):
        dur = ir.ExprCall(
            func=ir.ExprRefUnresolved(name="ps"),
            args=[ir.ExprConstant(value=500)],
        )
        assert _duration_to_ps_str(dur) == "500"


# ---------------------------------------------------------------------------
# Integration tests: coroutine emit produces correct wait code
# ---------------------------------------------------------------------------

def _simple_comp(name="Widget"):
    return ir.DataTypeComponent(name=name, super=None, fields=[], functions=[])


def _emit_wait_frame(dur_expr, tlm_sync_mode="") -> str:
    """Build a coroutine with a single wait and return the generated .c source."""
    comp = _simple_comp("TestComp")
    frame = SwCoroutineFrame(
        func_name="test_fn",
        comp_type_name="TestComp",
        continuations=[
            SwContinuation(index=0, stmts=[], suspend=SwSuspendWait(duration_expr=dur_expr), next_index=1),
            SwContinuation(index=1, stmts=[], suspend=None, next_index=None),
        ],
    )
    ctxt = SwContext(type_m={comp.name: comp})
    ctxt.tlm_sync_mode = tlm_sync_mode
    ctxt.sw_nodes[comp.name] = [frame]
    CEmitPass().run(ctxt)
    files = {name: content for name, content in ctxt.output_files}
    return files.get("TestComp.c", "")


class TestPreciseModeWait:
    """Without TLM mode, legacy ``zsp_timebase_wait`` must be emitted."""

    def test_precise_mode_uses_zsp_timebase_wait(self):
        dur = ir.ExprConstant(value=5)
        src = _emit_wait_frame(dur, tlm_sync_mode="")
        assert "zsp_timebase_wait" in src
        assert "ZSP_WAIT_PS" not in src

    def test_precise_mode_no_tlm_sync_attr(self):
        """When tlm_sync_mode is empty string, legacy path applies."""
        dur = ir.ExprConstant(value=1)
        src = _emit_wait_frame(dur, tlm_sync_mode="")
        assert "ZSP_WAIT_PS" not in src


class TestLTModeWait:
    """With ``tlm_sync_mode='lt'`` (or any non-empty value), ZSP_WAIT_PS is emitted."""

    def test_lt_mode_emits_zsp_wait_ps(self):
        dur = ir.ExprConstant(value=10000)
        src = _emit_wait_frame(dur, tlm_sync_mode="lt")
        assert "ZSP_WAIT_PS" in src
        assert "zsp_timebase_wait" not in src

    def test_precise_tlm_mode_emits_zsp_wait_ps(self):
        dur = ir.ExprConstant(value=10000)
        src = _emit_wait_frame(dur, tlm_sync_mode="precise")
        assert "ZSP_WAIT_PS" in src

    def test_lt_mode_ns_call_constant_folded(self):
        """wait(ns(10)) → ZSP_WAIT_PS(thread, 10000) in LT mode."""
        dur = ir.ExprCall(
            func=ir.ExprRefUnresolved(name="ns"),
            args=[ir.ExprConstant(value=10)],
        )
        src = _emit_wait_frame(dur, tlm_sync_mode="lt")
        assert "ZSP_WAIT_PS(thread, 10000)" in src

    def test_lt_mode_us_call_constant_folded(self):
        dur = ir.ExprCall(
            func=ir.ExprRefUnresolved(name="us"),
            args=[ir.ExprConstant(value=1)],
        )
        src = _emit_wait_frame(dur, tlm_sync_mode="lt")
        assert "ZSP_WAIT_PS(thread, 1000000)" in src

    def test_lt_mode_plain_integer(self):
        """Plain integer is treated as picoseconds."""
        dur = ir.ExprConstant(value=15000)
        src = _emit_wait_frame(dur, tlm_sync_mode="lt")
        assert "ZSP_WAIT_PS(thread, 15000)" in src

    def test_lt_mode_none_duration(self):
        """None duration emits ZSP_WAIT_PS with 0."""
        src = _emit_wait_frame(None, tlm_sync_mode="lt")
        assert "ZSP_WAIT_PS(thread, 0)" in src


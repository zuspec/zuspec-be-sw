"""Unit tests for CEmitPass (C struct and function generation)."""
import pytest
import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.rtl.component_classify import ComponentClassifyPass
from zuspec.be.sw.passes.rtl.next_state_split import NextStateSplitPass
from zuspec.be.sw.passes.rtl.comb_order import CombTopoSortPass
from zuspec.be.sw.passes.rtl.expr_lower import ExprLowerPass
from zuspec.be.sw.passes.rtl.c_emit import RtlCEmitPass as CEmitPass


def _build(py_cls):
    ctx = DataModelFactory().build(py_cls)
    return ctx.type_m[py_cls.__qualname__]


def _run_pipeline(py_cls) -> SwContext:
    comp = _build(py_cls)
    ctx = SwContext(rtl_component=comp)
    for cls in [ComponentClassifyPass, NextStateSplitPass, CombTopoSortPass, ExprLowerPass, CEmitPass]:
        ctx = cls().run(ctx)
    return ctx


def _get_file(ctx: SwContext, suffix: str) -> str:
    for name, content in ctx.output_files:
        if name.endswith(suffix):
            return content
    pytest.fail(f"No file with suffix {suffix!r} in output_files")


@pytest.fixture
def counter_ctx():
    @zdc.dataclass
    class Counter(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        enable: zdc.bit = zdc.input()
        count: zdc.b32 = zdc.output()

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _count(self):
            if self.reset:
                self.count = 0
            elif self.enable:
                self.count = self.count + 1

    return _run_pipeline(Counter)


def test_struct_has_current_and_nxt(counter_ctx):
    """Header has the _Regs sub-struct (with count) and embeds _regs/_nxt."""
    hdr = _get_file(counter_ctx, ".h")
    assert "count;" in hdr
    assert "_Regs" in hdr
    assert "_regs;" in hdr
    assert "_nxt;" in hdr


def test_init_zeroes_all_fields(counter_ctx):
    """_init() uses memset for _regs/_nxt zero-initialisation."""
    src = _get_file(counter_ctx, ".c")
    assert "memset(&self->_regs, 0," in src
    assert "memset(&self->_nxt,  0," in src


def test_clock_edge_calls_sync_then_advance(counter_ctx):
    """_clock_edge() calls sync body then _advance()."""
    src = _get_file(counter_ctx, ".c")
    assert "Counter_sync_count(self);" in src
    assert "Counter_advance(self);" in src
    # advance must come after sync call
    sync_pos = src.index("Counter_sync_count(self);")
    adv_pos = src.index("Counter_advance(self);")
    assert sync_pos < adv_pos


def test_advance_copies_nxt_to_current(counter_ctx):
    """_advance() does a single struct assignment: _regs = _nxt."""
    src = _get_file(counter_ctx, ".c")
    assert "self->_regs = self->_nxt;" in src


def test_comb_body_no_nxt_fields():
    """@comb writes go directly (no _nxt) even if same field is in nxt_fields."""
    @zdc.dataclass
    class C(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        a: zdc.bit = zdc.input()
        b: zdc.bit = zdc.output()

        @zdc.comb
        def _comb(self):
            self.b = self.a

    ctx = _run_pipeline(C)
    src = _get_file(ctx, ".c")
    # In eval_comb, b is written directly (not b_nxt)
    assert "self->b = self->a;" in src
    assert "b_nxt" not in src


def test_ctypes_fields_match_struct(counter_ctx):
    """_ctypes.py State._fields_ mirrors the C struct (uses _Regs sub-struct)."""
    py = _get_file(counter_ctx, "_ctypes.py")
    assert '"count"' in py
    assert '"_regs"' in py
    assert '"_nxt"' in py
    assert "ctypes.c_uint32" in py
    assert "ctypes.c_uint8" in py  # 1-bit fields map to uint8

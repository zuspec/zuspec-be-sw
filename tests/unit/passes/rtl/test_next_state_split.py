"""Unit tests for NextStateSplitPass."""
import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.rtl.next_state_split import NextStateSplitPass


def _build(py_cls):
    ctx = DataModelFactory().build(py_cls)
    return ctx.type_m[py_cls.__qualname__]


def _run(py_cls) -> SwContext:
    comp = _build(py_cls)
    ctx = SwContext(rtl_component=comp)
    return NextStateSplitPass().run(ctx)


def test_written_field_gets_shadow():
    """Field written in @sync → its name appears in nxt_fields."""
    @zdc.dataclass
    class C(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        count: zdc.b32 = zdc.output()

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _p(self):
            self.count = self.count + 1

    ctx = _run(C)
    assert "count" in ctx.rtl_nxt_fields


def test_readonly_field_unchanged():
    """Field only read in @sync (not written) → no _nxt."""
    @zdc.dataclass
    class C(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        enable: zdc.bit = zdc.input()
        count: zdc.b32 = zdc.output()

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _p(self):
            if self.enable:
                self.count = self.count + 1

    ctx = _run(C)
    assert "enable" not in ctx.rtl_nxt_fields
    assert "clock" not in ctx.rtl_nxt_fields
    assert "reset" not in ctx.rtl_nxt_fields
    assert "count" in ctx.rtl_nxt_fields


def test_read_before_write_in_body():
    """Fields read AND written get _nxt; read-only fields do not."""
    @zdc.dataclass
    class C(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        a: zdc.b32 = zdc.output()
        b: zdc.b32 = zdc.output()

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _p(self):
            self.a = self.b  # b read, a written

    ctx = _run(C)
    assert "a" in ctx.rtl_nxt_fields
    assert "b" not in ctx.rtl_nxt_fields


def test_multiple_sync_share_shadow():
    """Two @sync processes writing the same field → single _nxt entry."""
    @zdc.dataclass
    class C(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        x: zdc.b32 = zdc.output()

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _p1(self):
            self.x = 0

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _p2(self):
            self.x = 1

    ctx = _run(C)
    assert ctx.rtl_nxt_fields == {"x"}

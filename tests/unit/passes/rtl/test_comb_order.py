"""Unit tests for CombTopoSortPass."""
import pytest
import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.rtl.comb_order import CombTopoSortPass


def _build(py_cls):
    ctx = DataModelFactory().build(py_cls)
    return ctx.type_m[py_cls.__qualname__]


def _run(py_cls) -> SwContext:
    comp = _build(py_cls)
    ctx = SwContext(rtl_component=comp)
    return CombTopoSortPass().run(ctx)


def test_single_comb_trivial():
    """Single @comb → order has exactly that one function."""
    @zdc.dataclass
    class C(zdc.Component):
        a: zdc.bit = zdc.input()
        b: zdc.bit = zdc.output()

        @zdc.comb
        def _p(self):
            self.b = self.a

    ctx = _run(C)
    assert len(ctx.rtl_comb_order) == 1
    assert ctx.rtl_comb_order[0].name == "_p"


def test_independent_stable_order():
    """No dependency between combs → original insertion order preserved."""
    @zdc.dataclass
    class C(zdc.Component):
        a: zdc.bit = zdc.input()
        b: zdc.bit = zdc.output()
        c: zdc.bit = zdc.output()

        @zdc.comb
        def _pa(self):
            self.b = self.a

        @zdc.comb
        def _pb(self):
            self.c = self.a

    ctx = _run(C)
    assert [f.name for f in ctx.rtl_comb_order] == ["_pa", "_pb"]


def test_chain_abc_order():
    """A reads B's output, B reads C's output → emit C, B, A."""
    @zdc.dataclass
    class C(zdc.Component):
        x: zdc.bit = zdc.input()
        y: zdc.bit = zdc.output()
        z: zdc.bit = zdc.output()
        w: zdc.bit = zdc.output()

        @zdc.comb
        def _a(self):
            self.w = self.z   # reads z, written by _b

        @zdc.comb
        def _b(self):
            self.z = self.y   # reads y, written by _c

        @zdc.comb
        def _c(self):
            self.y = self.x

    ctx = _run(C)
    names = [f.name for f in ctx.rtl_comb_order]
    assert names.index("_c") < names.index("_b") < names.index("_a")


def test_no_processes_empty_order():
    """Component with no @comb → empty comb_order."""
    @zdc.dataclass
    class C(zdc.Component):
        x: zdc.b32 = zdc.output()

    ctx = _run(C)
    assert ctx.rtl_comb_order == []

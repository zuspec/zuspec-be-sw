"""Unit tests for ComponentClassifyPass."""
import pytest
import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory
from zuspec.dataclasses.ir import DataTypeComponent

from zuspec.be.sw.ir.protocol import EvalProtocol
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.rtl.component_classify import ComponentClassifyPass


def _build_comp(py_cls) -> DataTypeComponent:
    """Build IR DataTypeComponent from a Python class."""
    ctx = DataModelFactory().build(py_cls)
    return ctx.type_m[py_cls.__qualname__]


def _classify(py_cls) -> EvalProtocol:
    comp_ir = _build_comp(py_cls)
    ctx = SwContext(rtl_component=comp_ir)
    result = ComponentClassifyPass().run(ctx)
    return result.rtl_protocol


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_pure_sync_is_rtl():
    """@sync only → RTL."""
    @zdc.dataclass
    class PureSync(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        count: zdc.b32 = zdc.output()

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _proc(self):
            if self.reset:
                self.count = 0
            else:
                self.count = self.count + 1

    assert _classify(PureSync) == EvalProtocol.RTL


def test_pure_comb_is_rtl():
    """@comb only → RTL."""
    @zdc.dataclass
    class PureComb(zdc.Component):
        a: zdc.bit = zdc.input()
        b: zdc.bit = zdc.output()

        @zdc.comb
        def _proc(self):
            self.b = self.a

    assert _classify(PureComb) == EvalProtocol.RTL


def test_no_processes_is_algorithmic():
    """No processes → ALGORITHMIC (safe default)."""
    @zdc.dataclass
    class Empty(zdc.Component):
        x: zdc.b32 = zdc.output()

    assert _classify(Empty) == EvalProtocol.ALGORITHMIC


def test_sync_and_comb_is_rtl():
    """@sync + @comb, no await → RTL."""
    @zdc.dataclass
    class SyncAndComb(zdc.Component):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        enable: zdc.bit = zdc.input()
        count: zdc.b32 = zdc.output()
        count_en: zdc.b32 = zdc.output()

        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _sync(self):
            if self.reset:
                self.count = 0
            elif self.enable:
                self.count = self.count + 1

        @zdc.comb
        def _comb(self):
            self.count_en = self.count

    assert _classify(SyncAndComb) == EvalProtocol.RTL

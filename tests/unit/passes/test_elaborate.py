"""Tests for ElaborateSwPass."""
import zuspec.dataclasses as zdc
from zuspec.dataclasses import ir

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.elaborate import ElaborateSwPass, SwCompInst
from zuspec.be.sw.pipeline import SwPassManager


@zdc.dataclass
class Leaf(zdc.Component):
    pass


@zdc.dataclass
class Outer(zdc.Component):
    inner: Leaf = zdc.field()


def _build(py_cls):
    return zdc.DataModelFactory().build(py_cls)


def test_single_component():
    ctxt = _build(Leaf)
    sw_ctxt = ElaborateSwPass().run(SwContext(type_m=dict(ctxt.type_m)))
    assert sw_ctxt.root_inst is not None
    assert isinstance(sw_ctxt.root_inst, SwCompInst)
    assert "Leaf" in sw_ctxt.root_inst.type_name
    # inst_path is the lower-cased type name
    assert sw_ctxt.root_inst.inst_path == "leaf"
    assert sw_ctxt.root_inst.children == []


def test_nested_component():
    ctxt = _build(Outer)
    sw_ctxt = ElaborateSwPass().run(SwContext(type_m=dict(ctxt.type_m)))
    assert sw_ctxt.root_inst is not None
    assert "Outer" in sw_ctxt.root_inst.type_name
    # Should have one child for the 'inner' field
    assert len(sw_ctxt.root_inst.children) == 1
    child = sw_ctxt.root_inst.children[0]
    assert isinstance(child, SwCompInst)
    assert "Leaf" in child.type_name
    assert child.inst_path == "outer.inner"


def test_inst_m_populated():
    ctxt = _build(Outer)
    sw_ctxt = ElaborateSwPass().run(SwContext(type_m=dict(ctxt.type_m)))
    assert "outer" in sw_ctxt.inst_m
    assert "outer.inner" in sw_ctxt.inst_m


def test_pass_manager_returns_sw_context():
    ctxt = _build(Leaf)
    pm = SwPassManager()
    sw_ctxt = pm.run(ctxt)
    assert isinstance(sw_ctxt, SwContext)
    assert sw_ctxt.root_inst is not None


def test_pass_manager_inst_m_populated():
    ctxt = _build(Outer)
    pm = SwPassManager()
    sw_ctxt = pm.run(ctxt)
    assert len(sw_ctxt.inst_m) >= 2


def test_sw_comp_inst_is_sw_node():
    from zuspec.be.sw.ir.base import SwNode
    inst = SwCompInst(type_name="Foo", inst_path="foo")
    assert isinstance(inst, SwNode)


def test_config_top_selects_component():
    ctxt = _build(Outer)
    outer_name = None
    for name, dtype in ctxt.type_m.items():
        if isinstance(dtype, ir.DataTypeComponent) and "Outer" in (dtype.name or ""):
            outer_name = dtype.name
            break
    assert outer_name is not None
    sw_ctxt = ElaborateSwPass(config={"top": outer_name}).run(
        SwContext(type_m=dict(ctxt.type_m))
    )
    assert "Outer" in sw_ctxt.root_inst.type_name

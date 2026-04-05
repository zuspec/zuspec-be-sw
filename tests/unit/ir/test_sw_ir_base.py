"""Tests for SW IR base nodes (SwNode, SwContext)."""
import dataclasses as dc
from zuspec.dataclasses.ir.domain_node import DomainNode
from zuspec.dataclasses import ir

from zuspec.be.sw.ir.base import SwNode, SwContext
from zuspec.be.sw.ir.activity import SwSeqBlock


def test_sw_context_is_ir_context():
    ctxt = SwContext()
    assert isinstance(ctxt, ir.Context)


def test_sw_context_default_fields():
    ctxt = SwContext()
    assert ctxt.root_inst is None
    assert ctxt.inst_m == {}
    assert ctxt.sw_nodes == {}
    assert ctxt.c_type_m == {}
    assert ctxt.c_type_bodies == {}
    assert ctxt.output_files == []


def test_sw_context_type_m_from_parent():
    ctxt = SwContext()
    assert ctxt.type_m == {}


def test_sw_node_is_domain_node():
    # SwSeqBlock is a concrete SwNode we can instantiate
    node = SwSeqBlock()
    assert isinstance(node, SwNode)
    assert isinstance(node, DomainNode)


def test_sw_node_inputs_outputs_default_empty():
    node = SwSeqBlock()
    assert node.inputs() == []
    assert node.outputs() == []


def test_sw_node_repr_does_not_crash():
    node = SwSeqBlock()
    r = repr(node)
    assert "SwSeqBlock" in r


def test_sw_context_sw_nodes_mutable():
    from zuspec.be.sw.ir.activity import SwActionExec
    ctxt = SwContext()
    ctxt.sw_nodes["MyAction"] = [SwActionExec()]
    assert len(ctxt.sw_nodes["MyAction"]) == 1

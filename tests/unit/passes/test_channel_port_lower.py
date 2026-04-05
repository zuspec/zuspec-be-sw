"""Tests for ChannelPortLowerPass."""
import sys

import zuspec.dataclasses as zdc
from zuspec.dataclasses import ir
from zuspec.dataclasses.ir.fields import FieldKind

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.channel import SwFifo, SwFuncPtrStruct, SwFuncSlot
from zuspec.be.sw.passes.channel_port_lower import ChannelPortLowerPass


def _run(py_cls):
    ctxt = zdc.DataModelFactory().build(py_cls)
    sw_ctxt = SwContext(type_m=dict(ctxt.type_m))
    return ChannelPortLowerPass().run(sw_ctxt)


def test_channel_field_becomes_sw_fifo():
    from fixtures.channel_components import Producer
    sw_ctxt = _run(Producer)
    nodes = sw_ctxt.sw_nodes.get("Producer", [])
    fifos = [n for n in nodes if isinstance(n, SwFifo)]
    assert len(fifos) == 1
    assert fifos[0].field_name == "out_ch"


def test_channel_fifo_has_element_type():
    from fixtures.channel_components import Producer
    sw_ctxt = _run(Producer)
    fifo = next(n for n in sw_ctxt.sw_nodes["Producer"] if isinstance(n, SwFifo))
    assert fifo.element_type is not None
    assert isinstance(fifo.element_type, ir.DataTypeInt)


def test_consumer_channel_fifo():
    from fixtures.channel_components import Consumer
    sw_ctxt = _run(Consumer)
    nodes = sw_ctxt.sw_nodes.get("Consumer", [])
    fifos = [n for n in nodes if isinstance(n, SwFifo)]
    assert len(fifos) == 1
    assert fifos[0].field_name == "in_ch"


def test_protocol_port_field_becomes_func_ptr_struct():
    """A component with a ProtocolPort field gets a SwFuncPtrStruct."""
    # Build an IR component with a ProtocolPort field manually
    proto = ir.DataTypeProtocol(
        name="MemIface",
        methods=[
            ir.Function(name="read", args=ir.Arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
            )),
            ir.Function(name="write", args=ir.Arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
            )),
        ],
    )
    field = ir.Field(
        name="mem",
        datatype=ir.DataTypeRef(ref_name="MemIface"),
        kind=FieldKind.ProtocolPort,
    )
    comp = ir.DataTypeComponent(name="MemUser", super=None, fields=[field], functions=[])
    sw_ctxt = SwContext(type_m={"MemIface": proto, "MemUser": comp})
    sw_ctxt = ChannelPortLowerPass().run(sw_ctxt)
    nodes = sw_ctxt.sw_nodes.get("MemUser", [])
    structs = [n for n in nodes if isinstance(n, SwFuncPtrStruct)]
    assert len(structs) == 1


def test_protocol_port_slot_count_matches_methods():
    proto = ir.DataTypeProtocol(
        name="MyProto",
        methods=[
            ir.Function(name="m1", args=ir.Arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
            )),
            ir.Function(name="m2", args=ir.Arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
            )),
            ir.Function(name="m3", args=ir.Arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
            )),
        ],
    )
    field = ir.Field(
        name="proto",
        datatype=ir.DataTypeRef(ref_name="MyProto"),
        kind=FieldKind.ProtocolPort,
    )
    comp = ir.DataTypeComponent(name="ProtoUser", super=None, fields=[field], functions=[])
    sw_ctxt = SwContext(type_m={"MyProto": proto, "ProtoUser": comp})
    sw_ctxt = ChannelPortLowerPass().run(sw_ctxt)
    structs = [n for n in sw_ctxt.sw_nodes.get("ProtoUser", []) if isinstance(n, SwFuncPtrStruct)]
    assert len(structs[0].slots) == 3


def test_callable_port_single_slot():
    field = ir.Field(
        name="fetch",
        datatype=ir.DataTypeRef(ref_name="SomeFn"),
        kind=FieldKind.CallablePort,
    )
    comp = ir.DataTypeComponent(name="Caller", super=None, fields=[field], functions=[])
    sw_ctxt = SwContext(type_m={"Caller": comp})
    sw_ctxt = ChannelPortLowerPass().run(sw_ctxt)
    nodes = sw_ctxt.sw_nodes.get("Caller", [])
    structs = [n for n in nodes if isinstance(n, SwFuncPtrStruct)]
    assert len(structs) == 1
    assert len(structs[0].slots) == 1
    assert structs[0].struct_name == "fetch_fn_t"


def test_regular_field_not_lowered():
    """A plain Field does not produce any SW IR nodes."""
    field = ir.Field(name="x", datatype=ir.DataTypeInt(bits=32, signed=False))
    comp = ir.DataTypeComponent(name="Plain", super=None, fields=[field], functions=[])
    sw_ctxt = SwContext(type_m={"Plain": comp})
    sw_ctxt = ChannelPortLowerPass().run(sw_ctxt)
    assert sw_ctxt.sw_nodes.get("Plain", []) == []

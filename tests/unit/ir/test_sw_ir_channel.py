"""Tests for SW IR channel nodes."""
from zuspec.ir.core.domain_node import DomainNode
from zuspec.be.sw.ir.base import SwNode
from zuspec.be.sw.ir.channel import (
    SwFifo,
    SwFifoPush,
    SwFifoPop,
    SwFuncSlot,
    SwFuncPtrStruct,
    SwExportBind,
)


def test_sw_fifo_instantiation():
    node = SwFifo()
    assert isinstance(node, SwNode)
    assert isinstance(node, DomainNode)
    assert node.field_name is None
    assert node.element_type is None
    assert node.depth == 16


def test_sw_fifo_custom_depth():
    node = SwFifo(field_name="out_ch", depth=32)
    assert node.field_name == "out_ch"
    assert node.depth == 32


def test_sw_fifo_push_instantiation():
    node = SwFifoPush()
    assert isinstance(node, SwNode)
    assert node.fifo_ref is None
    assert node.value_expr is None


def test_sw_fifo_pop_instantiation():
    node = SwFifoPop()
    assert isinstance(node, SwNode)
    assert node.fifo_ref is None
    assert node.out_var is None


def test_sw_func_slot_instantiation():
    node = SwFuncSlot()
    assert isinstance(node, SwNode)
    assert node.slot_name is None
    assert node.signature is None


def test_sw_func_ptr_struct_instantiation():
    node = SwFuncPtrStruct()
    assert isinstance(node, SwNode)
    assert node.struct_name is None
    assert node.slots == []


def test_sw_func_ptr_struct_with_slots():
    s1 = SwFuncSlot(slot_name="read")
    s2 = SwFuncSlot(slot_name="write")
    struct = SwFuncPtrStruct(struct_name="MemIface_t", slots=[s1, s2])
    assert len(struct.slots) == 2
    assert struct.slots[0].slot_name == "read"


def test_sw_export_bind_instantiation():
    node = SwExportBind()
    assert isinstance(node, SwNode)
    assert node.struct_ref is None
    assert node.slot_name is None
    assert node.target_comp_path is None
    assert node.target_func_name is None


def test_all_channel_nodes_repr_do_not_crash():
    nodes = [
        SwFifo(),
        SwFifoPush(),
        SwFifoPop(),
        SwFuncSlot(),
        SwFuncPtrStruct(),
        SwExportBind(),
    ]
    for node in nodes:
        r = repr(node)
        assert type(node).__name__ in r

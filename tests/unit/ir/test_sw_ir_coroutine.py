"""Tests for SW IR coroutine nodes."""
from zuspec.dataclasses.ir.domain_node import DomainNode
from zuspec.be.sw.ir.base import SwNode
from zuspec.be.sw.ir.coroutine import (
    SwLocalVar,
    SwSuspendPoint,
    SwSuspendWait,
    SwSuspendCall,
    SwSuspendFifoPop,
    SwSuspendFifoPush,
    SwSuspendMutex,
    SwContinuation,
    SwCoroutineFrame,
)


def test_sw_local_var_instantiation():
    node = SwLocalVar()
    assert isinstance(node, SwNode)
    assert isinstance(node, DomainNode)
    assert node.var_name is None
    assert node.var_type is None


def test_sw_local_var_fields():
    node = SwLocalVar(var_name="x", var_type=None)
    assert node.var_name == "x"


def test_sw_suspend_wait_is_suspend_point():
    node = SwSuspendWait()
    assert isinstance(node, SwSuspendPoint)
    assert isinstance(node, SwNode)
    assert node.duration_expr is None


def test_sw_suspend_call_instantiation():
    node = SwSuspendCall()
    assert isinstance(node, SwSuspendPoint)
    assert node.call_expr is None


def test_sw_suspend_fifo_pop_instantiation():
    node = SwSuspendFifoPop()
    assert isinstance(node, SwSuspendPoint)
    assert node.fifo_field is None
    assert node.out_var is None


def test_sw_suspend_fifo_push_instantiation():
    node = SwSuspendFifoPush()
    assert isinstance(node, SwSuspendPoint)
    assert node.fifo_field is None
    assert node.value_expr is None


def test_sw_suspend_mutex_instantiation():
    node = SwSuspendMutex()
    assert isinstance(node, SwSuspendPoint)
    assert node.pool_field is None
    assert node.out_var is None


def test_sw_continuation_instantiation():
    node = SwContinuation()
    assert isinstance(node, SwNode)
    assert node.index == 0
    assert node.stmts == []
    assert node.suspend is None
    assert node.next_index is None


def test_sw_continuation_fields():
    susp = SwSuspendWait()
    cont = SwContinuation(index=1, stmts=[], suspend=susp, next_index=2)
    assert cont.index == 1
    assert cont.suspend is susp
    assert cont.next_index == 2


def test_sw_coroutine_frame_instantiation():
    node = SwCoroutineFrame()
    assert isinstance(node, SwNode)
    assert node.func_name is None
    assert node.comp_type_name is None
    assert node.locals_struct == []
    assert node.continuations == []


def test_sw_coroutine_frame_with_continuations():
    c0 = SwContinuation(index=0, suspend=SwSuspendWait(), next_index=1)
    c1 = SwContinuation(index=1)
    frame = SwCoroutineFrame(
        func_name="my_func_coro",
        comp_type_name="MyComp",
        continuations=[c0, c1],
    )
    assert len(frame.continuations) == 2
    assert frame.continuations[0].index == 0


def test_all_coroutine_nodes_repr_do_not_crash():
    nodes = [
        SwLocalVar(),
        SwSuspendWait(),
        SwSuspendCall(),
        SwSuspendFifoPop(),
        SwSuspendFifoPush(),
        SwSuspendMutex(),
        SwContinuation(),
        SwCoroutineFrame(),
    ]
    for node in nodes:
        r = repr(node)
        assert type(node).__name__ in r

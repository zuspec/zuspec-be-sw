"""Tests for CEmitPass (Phase 7)."""
from __future__ import annotations

import dataclasses as dc

import pytest

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.activity import (
    SwSchedulerNode, SwSeqBlock, SwParBlock, SwSelectNode, SwSelectBranch, SwActionExec
)
from zuspec.be.sw.ir.channel import SwFifo, SwFuncPtrStruct, SwFuncSlot
from zuspec.be.sw.ir.coroutine import (
    SwCoroutineFrame, SwContinuation, SwLocalVar, SwSuspendWait, SwSuspendFifoPop, SwSuspendMutex
)
from zuspec.be.sw.ir.resource import SwMutexAcquire, SwMutexRelease, SwIndexedSelect
from zuspec.be.sw.passes.c_emit import CEmitPass


def _simple_comp(name="Widget", fields=None, functions=None):
    return ir.DataTypeComponent(
        name=name, super=None,
        fields=fields or [],
        functions=functions or [],
    )


def _run(comp: ir.DataTypeComponent, nodes: list = None):
    ctxt = SwContext(type_m={comp.name: comp})
    if nodes:
        ctxt.sw_nodes[comp.name] = nodes
    CEmitPass().run(ctxt)
    files = {name: content for name, content in ctxt.output_files}
    return files


# ---------------------------------------------------------------------------
# Struct definition
# ---------------------------------------------------------------------------

def test_emit_struct_has_correct_fields():
    field = ir.Field(name="counter", datatype=ir.DataTypeInt(bits=32, signed=False))
    comp = _simple_comp("Counter", fields=[field])
    files = _run(comp)
    # Struct definition is now in the header (for sub-component embedding)
    assert "uint32_t counter;" in files["Counter.h"]


def test_emit_struct_includes_fifo_field():
    comp = _simple_comp("Prod")
    fifo = SwFifo(field_name="out_ch", element_type=ir.DataTypeInt(bits=32, signed=False))
    files = _run(comp, [fifo])
    assert "out_ch_fifo" in files["Prod.c"]


# ---------------------------------------------------------------------------
# Init function
# ---------------------------------------------------------------------------

def test_emit_init_fn_initialises_fields():
    comp = _simple_comp("Comp")
    fifo = SwFifo(field_name="data", depth=32)
    files = _run(comp, [fifo])
    assert "zsp_fifo_init" in files["Comp.c"]
    assert "32" in files["Comp.c"]


# ---------------------------------------------------------------------------
# Sequential block
# ---------------------------------------------------------------------------

def test_emit_seq_block_sequential_calls():
    action1 = SwActionExec()
    action2 = SwActionExec()
    seq = SwSeqBlock(children=[action1, action2])
    sched = SwSchedulerNode(root=seq)
    comp = _simple_comp("SeqComp")
    files = _run(comp, [sched])
    assert "SeqComp_run" in files["SeqComp.c"]


# ---------------------------------------------------------------------------
# Parallel block
# ---------------------------------------------------------------------------

def test_emit_par_block_fork_join():
    par = SwParBlock(children=[SwActionExec(), SwActionExec()])
    sched = SwSchedulerNode(root=par)
    comp = _simple_comp("ParComp")
    files = _run(comp, [sched])
    src = files["ParComp.c"]
    assert "zsp_par_block_t" in src
    assert "zsp_par_block_join" in src


# ---------------------------------------------------------------------------
# Select node
# ---------------------------------------------------------------------------

def test_emit_select_uses_weighted_random():
    b1 = SwSelectBranch(body=SwSeqBlock())
    b2 = SwSelectBranch(body=SwSeqBlock())
    sel = SwSelectNode(branches=[b1, b2])
    sched = SwSchedulerNode(root=sel)
    comp = _simple_comp("SelComp")
    files = _run(comp, [sched])
    src = files["SelComp.c"]
    assert "zsp_select_t" in src
    assert "2 branches" in src


# ---------------------------------------------------------------------------
# Sync function
# ---------------------------------------------------------------------------

def test_emit_sync_function_no_state_machine():
    func = ir.Function(
        name="do_work",
        args=ir.Arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[ir.StmtPass()],
        is_async=True,
        metadata={"sync_convertible": True},
    )
    comp = _simple_comp("SyncComp", functions=[func])
    files = _run(comp)
    src = files["SyncComp.c"]
    assert "SyncComp_do_work" in src
    assert "switch" not in src


# ---------------------------------------------------------------------------
# Coroutine
# ---------------------------------------------------------------------------

def test_emit_coroutine_switch_case_structure():
    frame = SwCoroutineFrame(
        func_name="Coro_task",
        comp_type_name="Coro",
        continuations=[
            SwContinuation(index=0, stmts=[], suspend=SwSuspendWait()),
            SwContinuation(index=1, stmts=[]),
        ],
    )
    comp = _simple_comp("Coro")
    files = _run(comp, [frame])
    src = files["Coro.c"]
    assert "switch (idx)" in src
    assert "case 0:" in src
    assert "case 1:" in src


def test_emit_suspend_wait_breaks():
    frame = SwCoroutineFrame(
        func_name="Waiter_run",
        comp_type_name="Waiter",
        continuations=[
            SwContinuation(
                index=0,
                stmts=[],
                suspend=SwSuspendWait(duration_expr=ir.ExprConstant(value=5)),
            ),
            SwContinuation(index=1, stmts=[]),
        ],
    )
    comp = _simple_comp("Waiter")
    files = _run(comp, [frame])
    src = files["Waiter.c"]
    assert "zsp_timebase_wait" in src
    assert "5" in src


def test_emit_suspend_fifo_pop():
    frame = SwCoroutineFrame(
        func_name="Cons_consume",
        comp_type_name="Cons",
        continuations=[
            SwContinuation(
                index=0, stmts=[],
                suspend=SwSuspendFifoPop(fifo_field="in_ch"),
            ),
            SwContinuation(index=1, stmts=[]),
        ],
    )
    comp = _simple_comp("Cons")
    files = _run(comp, [frame])
    assert "in_ch_fifo" in files["Cons.c"]


def test_emit_suspend_mutex():
    frame = SwCoroutineFrame(
        func_name="Worker_work",
        comp_type_name="Worker",
        continuations=[
            SwContinuation(
                index=0, stmts=[],
                suspend=SwSuspendMutex(pool_field="pool"),
            ),
            SwContinuation(index=1, stmts=[]),
        ],
    )
    comp = _simple_comp("Worker")
    files = _run(comp, [frame])
    assert "pool_mutex" in files["Worker.c"]


# ---------------------------------------------------------------------------
# Fifo declaration
# ---------------------------------------------------------------------------

def test_emit_fifo_decl_and_init():
    fifo = SwFifo(field_name="buf", depth=64)
    comp = _simple_comp("FifoComp")
    files = _run(comp, [fifo])
    src = files["FifoComp.c"]
    assert "buf_fifo" in src
    assert "zsp_fifo_init" in src


# ---------------------------------------------------------------------------
# Func-ptr struct
# ---------------------------------------------------------------------------

def test_emit_func_ptr_struct():
    fps = SwFuncPtrStruct(
        struct_name="MemIface_t",
        slots=[SwFuncSlot(slot_name="read"), SwFuncSlot(slot_name="write")],
    )
    comp = _simple_comp("MemComp")
    files = _run(comp, [fps])
    src = files["MemComp.c"]
    assert "MemIface_t" in src
    assert "read" in src
    assert "write" in src


# ---------------------------------------------------------------------------
# Mutex acquire/release paired
# ---------------------------------------------------------------------------

def test_emit_mutex_acquire_release_paired():
    pool_expr = ir.ExprAttribute(
        value=ir.TypeExprRefSelf(), attr="pool"
    )
    acq = SwMutexAcquire(pool_expr=pool_expr, out_var="unit")
    rel = SwMutexRelease(pool_expr=pool_expr, acquire_ref=acq)
    comp = _simple_comp("LockComp")
    files = _run(comp, [acq, rel])
    src = files["LockComp.c"]
    assert "zsp_mutex_acquire" in src
    assert "zsp_mutex_release" in src


# ---------------------------------------------------------------------------
# Header file
# ---------------------------------------------------------------------------

def test_header_has_include_guard():
    comp = _simple_comp("GuardComp")
    files = _run(comp)
    h = files["GuardComp.h"]
    assert "#ifndef _GUARDCOMP_H" in h
    assert "#define _GUARDCOMP_H" in h
    assert "#endif" in h


def test_header_has_init_declaration():
    comp = _simple_comp("InitComp")
    files = _run(comp)
    h = files["InitComp.h"]
    assert "InitComp_init" in h

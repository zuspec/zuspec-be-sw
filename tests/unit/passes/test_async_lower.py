"""Tests for AsyncLowerPass (Phase 6)."""
from __future__ import annotations

import dataclasses as dc
from typing import List

import pytest

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.coroutine import (
    SwCoroutineFrame,
    SwContinuation,
    SwSuspendWait,
    SwSuspendFifoPop,
    SwSuspendFifoPush,
    SwSuspendMutex,
    SwSuspendCall,
)
from zuspec.be.sw.passes.async_lower import (
    AsyncLowerPass,
    _classify_all,
    _split_at_awaits,
    _classify_await,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_args() -> ir.Arguments:
    return ir.Arguments(
        posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
    )


def _make_func(name: str, body: list, is_async=True, is_import=False) -> ir.Function:
    return ir.Function(
        name=name,
        args=_make_args(),
        body=body,
        is_async=is_async,
        is_import=is_import,
    )


def _make_comp(name: str, functions: list) -> ir.DataTypeComponent:
    return ir.DataTypeComponent(name=name, super=None, fields=[], functions=functions)


def _make_await(inner: ir.Expr) -> ir.ExprAwait:
    return ir.ExprAwait(value=inner)


def _wait_call(n: int = 1) -> ir.ExprCall:
    return ir.ExprCall(
        func=ir.ExprRefUnresolved(name="wait"),
        args=[ir.ExprConstant(value=n)],
    )


def _chan_get(chan_name: str = "ch") -> ir.ExprCall:
    return ir.ExprCall(
        func=ir.ExprAttribute(
            value=ir.ExprRefLocal(name=chan_name),
            attr="get",
        ),
        args=[],
    )


def _chan_put(chan_name: str = "ch", val: int = 42) -> ir.ExprCall:
    return ir.ExprCall(
        func=ir.ExprAttribute(
            value=ir.ExprRefLocal(name=chan_name),
            attr="put",
        ),
        args=[ir.ExprConstant(value=val)],
    )


def _lock_call(pool_name: str = "pool") -> ir.ExprCall:
    return ir.ExprCall(
        func=ir.ExprAttribute(
            value=ir.ExprRefLocal(name=pool_name),
            attr="lock",
        ),
        args=[],
    )


def _ctx(*comps: ir.DataTypeComponent) -> SwContext:
    return SwContext(type_m={c.name: c for c in comps})


# ===========================================================================
# Classification tests
# ===========================================================================

def test_no_await_is_sync_convertible():
    func = _make_func("run", body=[ir.StmtPass()])
    comp = _make_comp("Foo", [func])
    sync_map = _classify_all(_ctx(comp))
    assert sync_map["Foo.run"] is True


def test_single_await_not_convertible():
    func = _make_func("run", body=[
        ir.StmtExpr(expr=_make_await(_wait_call())),
    ])
    comp = _make_comp("Bar", [func])
    sync_map = _classify_all(_ctx(comp))
    assert sync_map["Bar.run"] is False


def test_channel_get_not_convertible():
    func = _make_func("consume", body=[
        ir.StmtExpr(expr=_make_await(_chan_get("ch"))),
    ])
    comp = _make_comp("Cons", [func])
    sync_map = _classify_all(_ctx(comp))
    assert sync_map["Cons.consume"] is False


def test_mutex_acquire_not_convertible():
    func = _make_func("work", body=[
        ir.StmtExpr(expr=_make_await(_lock_call("pool"))),
    ])
    comp = _make_comp("Worker", [func])
    sync_map = _classify_all(_ctx(comp))
    assert sync_map["Worker.work"] is False


def test_protocol_method_not_convertible():
    proto = ir.DataTypeProtocol(name="MemProto", methods=[_make_func("read", [])])
    comp = _make_comp("Stub", [_make_func("read", [])])
    ctxt = SwContext(type_m={"MemProto": proto, "Stub": comp})
    sync_map = _classify_all(ctxt)
    # protocol method itself is not sync-convertible
    assert sync_map.get("MemProto.read") is False


def test_import_function_not_convertible():
    func = _make_func("call_hw", body=[], is_import=True)
    comp = _make_comp("HW", [func])
    sync_map = _classify_all(_ctx(comp))
    assert sync_map["HW.call_hw"] is False


def test_transitive_call_to_async_not_convertible():
    # inner has await → not sync; outer calls inner → not sync either
    inner = _make_func("inner", body=[
        ir.StmtExpr(expr=_make_await(_wait_call())),
    ])
    outer = _make_func("outer", body=[
        ir.StmtExpr(expr=ir.ExprCall(
            func=ir.ExprRefLocal(name="inner"), args=[]
        )),
    ])
    comp = _make_comp("Comp", [inner, outer])
    sync_map = _classify_all(_ctx(comp))
    assert sync_map["Comp.inner"] is False
    assert sync_map["Comp.outer"] is False


def test_transitive_call_to_sync_ok():
    # inner has no await → sync; outer calls inner → sync too
    inner = _make_func("helper", body=[ir.StmtPass()])
    outer = _make_func("run", body=[
        ir.StmtExpr(expr=ir.ExprCall(
            func=ir.ExprRefLocal(name="helper"), args=[]
        )),
    ])
    comp = _make_comp("Clean", [inner, outer])
    sync_map = _classify_all(_ctx(comp))
    assert sync_map["Clean.run"] is True


# ===========================================================================
# Coroutine splitting tests
# ===========================================================================

def test_single_wait_two_continuations():
    stmts = [
        ir.StmtExpr(expr=_make_await(_wait_call())),
    ]
    frame = _split_at_awaits(stmts, "Comp", "run")
    assert len(frame.continuations) == 2


def test_multiple_waits_n_plus_one_continuations():
    stmts = [
        ir.StmtExpr(expr=_make_await(_wait_call())),
        ir.StmtExpr(expr=_make_await(_wait_call())),
        ir.StmtExpr(expr=_make_await(_wait_call())),
    ]
    frame = _split_at_awaits(stmts, "Comp", "run")
    assert len(frame.continuations) == 4


def test_local_var_before_await_captured():
    # x = 1; await wait(1); y = x  → x must be in locals_struct
    stmts = [
        ir.StmtAssign(
            targets=[ir.ExprRefLocal(name="x")],
            value=ir.ExprConstant(value=1),
        ),
        ir.StmtExpr(expr=_make_await(_wait_call())),
        ir.StmtAssign(
            targets=[ir.ExprRefLocal(name="y")],
            value=ir.ExprRefLocal(name="x"),
        ),
    ]
    frame = _split_at_awaits(stmts, "Comp", "run")
    frame_var_names = {v.var_name for v in frame.locals_struct}
    assert "x" in frame_var_names


def test_local_var_after_await_not_captured():
    # await wait(1); y = 5  → y is local to last continuation
    stmts = [
        ir.StmtExpr(expr=_make_await(_wait_call())),
        ir.StmtAssign(
            targets=[ir.ExprRefLocal(name="y")],
            value=ir.ExprConstant(value=5),
        ),
    ]
    frame = _split_at_awaits(stmts, "Comp", "run")
    frame_var_names = {v.var_name for v in frame.locals_struct}
    assert "y" not in frame_var_names


def test_local_var_straddling_two_awaits_captured():
    # x = 1; await; await; use x  → x in locals_struct
    stmts = [
        ir.StmtAssign(
            targets=[ir.ExprRefLocal(name="x")],
            value=ir.ExprConstant(value=1),
        ),
        ir.StmtExpr(expr=_make_await(_wait_call())),
        ir.StmtExpr(expr=_make_await(_wait_call())),
        ir.StmtAssign(
            targets=[ir.ExprRefLocal(name="z")],
            value=ir.ExprRefLocal(name="x"),
        ),
    ]
    frame = _split_at_awaits(stmts, "Comp", "run")
    frame_var_names = {v.var_name for v in frame.locals_struct}
    assert "x" in frame_var_names


def test_channel_get_produces_sw_suspend_fifo_pop():
    await_expr = ir.ExprAwait(value=_chan_get("ch"))
    suspend = _classify_await(await_expr)
    assert isinstance(suspend, SwSuspendFifoPop)
    assert suspend.fifo_field == "ch"


def test_channel_put_produces_sw_suspend_fifo_push():
    await_expr = ir.ExprAwait(value=_chan_put("out_ch", 99))
    suspend = _classify_await(await_expr)
    assert isinstance(suspend, SwSuspendFifoPush)
    assert suspend.fifo_field == "out_ch"


def test_mutex_produces_sw_suspend_mutex():
    await_expr = ir.ExprAwait(value=_lock_call("my_pool"))
    suspend = _classify_await(await_expr)
    assert isinstance(suspend, SwSuspendMutex)
    assert suspend.pool_field == "my_pool"


def test_nested_if_with_await_in_branch():
    """An await inside an if-branch still produces two continuations."""
    stmts = [
        ir.StmtIf(
            test=ir.ExprConstant(value=True),
            body=[ir.StmtExpr(expr=_make_await(_wait_call()))],
            orelse=[],
        ),
        ir.StmtPass(),
    ]
    frame = _split_at_awaits(stmts, "Comp", "run")
    # At least 2 continuations since there's an await
    assert len(frame.continuations) >= 2


# ===========================================================================
# Full pass integration tests
# ===========================================================================

def test_pass_marks_sync_convertible():
    func = _make_func("helper", body=[ir.StmtPass()])
    comp = _make_comp("Sync", [func])
    ctxt = _ctx(comp)
    AsyncLowerPass().run(ctxt)
    assert func.metadata.get("sync_convertible") is True


def test_pass_produces_coroutine_frame():
    func = _make_func("task", body=[
        ir.StmtExpr(expr=_make_await(_wait_call())),
    ])
    comp = _make_comp("Async", [func])
    ctxt = _ctx(comp)
    AsyncLowerPass().run(ctxt)
    nodes = ctxt.sw_nodes.get("Async", [])
    frames = [n for n in nodes if isinstance(n, SwCoroutineFrame)]
    assert len(frames) == 1
    assert frames[0].comp_type_name == "Async"

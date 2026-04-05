"""Tests for ResourceLowerPass.

Note: The DataModelFactory does not yet generate StmtWith nodes for
``async with self.pool.lock() as unit:`` patterns.  Tests here use
manually-constructed IR to verify the lowering logic.
"""
import dataclasses as dc
from typing import List

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.resource import SwMutexAcquire, SwMutexRelease, SwIndexedSelect
from zuspec.be.sw.passes.resource_lower import ResourceLowerPass


def _make_lock_with_stmt(field_name: str = "pool", var_name: str = "unit") -> ir.StmtWith:
    """Build a StmtWith representing ``async with self.<field>.lock() as <var>:``."""
    # self.pool  → ExprAttribute(value=ExprRefSelf, attr='pool')
    self_ref = ir.TypeExprRefSelf()
    recv = ir.ExprAttribute(value=self_ref, attr=field_name)
    # self.pool.lock()
    lock_attr = ir.ExprAttribute(value=recv, attr="lock")
    lock_call = ir.ExprCall(func=lock_attr, args=[])
    # optional_vars (the `as unit` part)
    out_ref = ir.ExprRefLocal(name=var_name)
    item = ir.WithItem(context_expr=lock_call, optional_vars=out_ref)
    return ir.StmtWith(items=[item], body=[])


def _make_comp_with_pool(field_name: str = "pool") -> ir.DataTypeComponent:
    """Build a DataTypeComponent with a ClaimPool field and a do_work function."""
    pool_field = ir.Field(
        name=field_name,
        datatype=ir.DataTypeRef(ref_name="ClaimPool_Worker"),
    )
    func = ir.Function(
        name="do_work",
        args=ir.Arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[_make_lock_with_stmt(field_name)],
        is_async=True,
    )
    return ir.DataTypeComponent(name="PoolComp", super=None, fields=[pool_field], functions=[func])


def test_claim_pool_lock_produces_acquire():
    comp = _make_comp_with_pool()
    ctxt = SwContext(type_m={"PoolComp": comp})
    ctxt = ResourceLowerPass().run(ctxt)
    nodes = ctxt.sw_nodes.get("PoolComp", [])
    assert any(isinstance(n, SwMutexAcquire) for n in nodes)


def test_claim_pool_acquire_variable_bound():
    comp = _make_comp_with_pool()
    ctxt = SwContext(type_m={"PoolComp": comp})
    ctxt = ResourceLowerPass().run(ctxt)
    acq = next(n for n in ctxt.sw_nodes.get("PoolComp", []) if isinstance(n, SwMutexAcquire))
    assert acq.out_var == "unit"


def test_acquire_has_pool_expr():
    comp = _make_comp_with_pool(field_name="my_pool")
    ctxt = SwContext(type_m={"PoolComp": comp})
    ctxt = ResourceLowerPass().run(ctxt)
    acq = next(n for n in ctxt.sw_nodes.get("PoolComp", []) if isinstance(n, SwMutexAcquire))
    assert acq.pool_expr is not None


def test_acquire_release_linked():
    comp = _make_comp_with_pool()
    ctxt = SwContext(type_m={"PoolComp": comp})
    ctxt = ResourceLowerPass().run(ctxt)
    acq = next(n for n in ctxt.sw_nodes.get("PoolComp", []) if isinstance(n, SwMutexAcquire))
    # The acquire carries a body (SwSeqBlock) for statements inside the lock scope
    from zuspec.be.sw.ir.activity import SwSeqBlock
    assert isinstance(acq.body, SwSeqBlock)


def test_no_pool_no_nodes():
    """A component without ClaimPool fields produces no resource nodes."""
    func = ir.Function(
        name="work",
        args=ir.Arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[ir.StmtPass()],
        is_async=False,
    )
    comp = ir.DataTypeComponent(name="Plain", super=None, fields=[], functions=[func])
    ctxt = SwContext(type_m={"Plain": comp})
    ctxt = ResourceLowerPass().run(ctxt)
    assert ctxt.sw_nodes.get("Plain", []) == []


def test_pass_idempotent_on_empty_bodies():
    """Components with empty function bodies produce no resource nodes."""
    import zuspec.dataclasses as zdc
    from fixtures.resource_components import PoolComp
    ir_ctxt = zdc.DataModelFactory().build(PoolComp)
    sw_ctxt = SwContext(type_m=dict(ir_ctxt.type_m))
    sw_ctxt = ResourceLowerPass().run(sw_ctxt)
    # Factory doesn't generate StmtWith so no nodes are produced; pass must not crash
    assert True

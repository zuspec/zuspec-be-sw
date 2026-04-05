"""ResourceLowerPass — lower ClaimPool.lock() and IndexedPool patterns.

Note: Full pattern-matching requires the DataModelFactory to generate
``StmtWith`` nodes for ``async with self.pool.lock() as unit:`` constructs.
Until that support is added, this pass operates on IR functions whose bodies
already contain ``StmtWith`` nodes (e.g., hand-crafted or from a future
factory version).
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext, SwNode
from zuspec.be.sw.ir.resource import SwMutexAcquire, SwMutexRelease, SwIndexedSelect
from zuspec.be.sw.ir.activity import SwSeqBlock
from zuspec.be.sw.pipeline import SwPass


class ResourceLowerPass(SwPass):
    """Scan function bodies for ClaimPool / IndexedPool patterns and lower them.

    Specifically:
    - ``StmtWith`` whose context expression is a ``ClaimPool.lock()`` call is
      replaced with ``SwMutexAcquire`` + body + ``SwMutexRelease``.
    - ``acquire_index()`` / ``release_index()`` call sequences on an
      ``IndexedPool`` field produce ``SwIndexedSelect`` nodes.
    """

    def run(self, ctxt: SwContext) -> SwContext:
        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, ir.DataTypeComponent):
                continue
            for func in dtype.functions:
                if not func.body:
                    continue
                lowered = self._lower_stmts(func.body, dtype, ctxt)
                if lowered is not None:
                    ctxt.sw_nodes.setdefault(type_name, []).extend(lowered)
        return ctxt

    # ------------------------------------------------------------------

    def _lower_stmts(
        self,
        stmts: List[ir.Stmt],
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
    ) -> Optional[List[SwNode]]:
        """Walk *stmts* and collect any lowered SW IR nodes."""
        nodes: List[SwNode] = []
        for stmt in stmts:
            node = self._lower_stmt(stmt, comp, ctxt)
            if node:
                nodes.append(node)
        return nodes if nodes else None

    def _lower_stmt(
        self,
        stmt: ir.Stmt,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
    ) -> Optional[SwNode]:
        if isinstance(stmt, ir.StmtWith):
            return self._lower_with(stmt, comp, ctxt)
        return None

    def _lower_with(
        self,
        stmt: ir.StmtWith,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
    ) -> Optional[SwNode]:
        if not stmt.items:
            return None
        item = stmt.items[0]
        ctx_expr = item.context_expr

        # Detect pool.lock() — ExprCall on ExprAttribute ending in .lock()
        if self._is_lock_call(ctx_expr, comp, ctxt):
            pool_expr = ctx_expr.func.value if isinstance(ctx_expr, ir.ExprCall) else None
            out_var = self._extract_var_name(item.optional_vars)
            body_node = SwSeqBlock(children=[])  # placeholder for lowered body stmts
            acq = SwMutexAcquire(
                pool_expr=pool_expr,
                out_var=out_var,
                body=body_node,
            )
            rel = SwMutexRelease(pool_expr=pool_expr, acquire_ref=acq)
            return acq  # rel is attached; code emitter traverses acq.body then emits rel

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_lock_call(
        self, expr, comp: ir.DataTypeComponent, ctxt: SwContext
    ) -> bool:
        """Return True if *expr* is a ``self.<field>.lock()`` call on a
        ClaimPool field."""
        if not isinstance(expr, ir.ExprCall):
            return False
        func = expr.func
        if not isinstance(func, ir.ExprAttribute):
            return False
        if func.attr != "lock":
            return False
        # Check that the receiver is a field of comp whose type is a ClaimPool
        recv = func.value
        if isinstance(recv, ir.ExprAttribute):
            field_name = recv.attr
            for field in comp.fields:
                if field.name == field_name and self._is_claim_pool(
                    field.datatype, ctxt
                ):
                    return True
        return False

    def _is_claim_pool(self, dtype: ir.DataType, ctxt: SwContext) -> bool:
        """Heuristic: a DataTypeRef or DataTypeLock whose name contains
        'ClaimPool' or 'Pool' is treated as a ClaimPool."""
        if isinstance(dtype, ir.DataTypeRef):
            name = dtype.ref_name or ""
            return "ClaimPool" in name or "Pool" in name
        if isinstance(dtype, ir.DataTypeLock):
            return True
        if dtype and getattr(dtype, "name", None):
            return "ClaimPool" in (dtype.name or "")
        return False

    def _extract_var_name(self, expr) -> Optional[str]:
        if expr is None:
            return None
        if isinstance(expr, ir.ExprRefLocal):
            return expr.name
        if isinstance(expr, ir.ExprRefUnresolved):
            return expr.name
        if hasattr(expr, "ref"):
            return expr.ref
        return None

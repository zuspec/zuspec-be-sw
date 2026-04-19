"""
ComponentClassifyPass — infers the EvalProtocol for a component.

Classification rules (design §14):
  - @sync only (or mix @sync/@comb, no await) → RTL
  - @comb only (no await)                      → RTL
  - await present anywhere                     → ALGORITHMIC (or MLS if @sync also present)
  - @sync + await in same component            → MLS
  - No processes at all                        → ALGORITHMIC (safe default)
"""
from __future__ import annotations

from zuspec.dataclasses import ir
from zuspec.ir.core.expr import ExprAwait
from zuspec.ir.core.stmt import (
    Stmt, StmtIf, StmtFor, StmtWhile, StmtExpr, StmtAssign,
    StmtAugAssign, StmtReturn, StmtAnnAssign,
)

from zuspec.be.sw.ir.protocol import EvalProtocol
from zuspec.be.sw.ir.base import SwContext


def _has_await(stmts: list) -> bool:
    """Return True if any statement (or sub-statement) contains an await."""
    for stmt in stmts:
        if isinstance(stmt, StmtExpr):
            if _expr_has_await(stmt.expr):
                return True
        elif isinstance(stmt, (StmtIf,)):
            if _has_await(stmt.body) or _has_await(stmt.orelse):
                return True
        elif isinstance(stmt, (StmtFor, StmtWhile)):
            if _has_await(stmt.body):
                return True
        elif isinstance(stmt, (StmtAssign, StmtAugAssign, StmtAnnAssign)):
            pass
        # Any other stmt type — descend into known body-carrying attrs
        else:
            for attr in ("body", "orelse", "handlers", "finalbody"):
                sub = getattr(stmt, attr, None)
                if sub and isinstance(sub, list):
                    if _has_await(sub):
                        return True
    return False


def _expr_has_await(expr) -> bool:
    """Return True if ``expr`` is or contains an ExprAwait."""
    if isinstance(expr, ExprAwait):
        return True
    for attr in ("value", "lhs", "rhs", "test", "body", "orelse"):
        child = getattr(expr, attr, None)
        if child is not None and hasattr(child, "__class__"):
            if _expr_has_await(child):
                return True
    return False


class ComponentClassifyPass:
    """Determine EvalProtocol and store it in ``ctx.rtl_protocol``."""

    def run(self, ctx: SwContext) -> SwContext:
        comp = ctx.rtl_component

        has_sync = bool(comp.sync_processes)
        has_comb = bool(comp.comb_processes)

        # Check for await in any process body
        has_await = False
        for fn in comp.sync_processes + comp.comb_processes:
            if fn.is_async or _has_await(fn.body):
                has_await = True
                break

        if has_await and has_sync:
            ctx.rtl_protocol = EvalProtocol.MLS
        elif has_await:
            ctx.rtl_protocol = EvalProtocol.ALGORITHMIC
        elif has_sync or has_comb:
            ctx.rtl_protocol = EvalProtocol.RTL
        else:
            # No processes at all
            ctx.rtl_protocol = EvalProtocol.ALGORITHMIC

        return ctx

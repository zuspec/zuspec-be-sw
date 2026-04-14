"""
CombTopoSortPass — topologically sort @comb processes by data dependency.

Sensitivity analysis: for each @comb function we collect the set of
field *indices* it reads and the set it writes.  Then we order functions
so that writers come before readers (i.e., if A reads a field that B
writes, B is emitted before A).

``ctx.rtl_comb_order`` is set to the sorted list of @comb ``Function`` objects.

Raises ``ValueError`` on a combinational loop (cycle in the dependency graph).
"""
from __future__ import annotations

from typing import List, Set

from zuspec.dataclasses import ir
from zuspec.dataclasses.ir.expr import ExprRefField, TypeExprRefSelf
from zuspec.dataclasses.ir.stmt import (
    Stmt, StmtAssign, StmtAugAssign, StmtIf, StmtFor, StmtWhile, StmtExpr,
    StmtReturn,
)

from zuspec.be.sw.ir.base import SwContext


# ---------------------------------------------------------------------------
# Field-index collection helpers
# ---------------------------------------------------------------------------

def _collect_reads(expr, reads: Set[int]) -> None:
    """Recursively collect field indices *read* in an expression."""
    if expr is None:
        return
    if isinstance(expr, ExprRefField) and isinstance(expr.base, TypeExprRefSelf):
        reads.add(expr.index)
    for attr in ("base", "lhs", "rhs", "value", "test", "body", "orelse",
                 "left", "comparators", "values", "elts"):
        child = getattr(expr, attr, None)
        if child is None:
            continue
        if isinstance(child, list):
            for c in child:
                _collect_reads(c, reads)
        else:
            _collect_reads(child, reads)


def _collect_stmt_reads_writes(stmts: list, reads: Set[int], writes: Set[int]) -> None:
    for stmt in stmts:
        if isinstance(stmt, StmtAssign):
            # The value is read
            _collect_reads(stmt.value, reads)
            # Each target is written (don't count as read)
            for tgt in stmt.targets:
                if isinstance(tgt, ExprRefField) and isinstance(tgt.base, TypeExprRefSelf):
                    writes.add(tgt.index)
        elif isinstance(stmt, StmtAugAssign):
            # target is both read and written
            tgt = stmt.target
            if isinstance(tgt, ExprRefField) and isinstance(tgt.base, TypeExprRefSelf):
                reads.add(tgt.index)
                writes.add(tgt.index)
            _collect_reads(stmt.value, reads)
        elif isinstance(stmt, StmtExpr):
            _collect_reads(stmt.expr, reads)
        elif isinstance(stmt, StmtReturn):
            if stmt.value:
                _collect_reads(stmt.value, reads)
        else:
            # Generic descent
            for attr in ("body", "orelse", "handlers", "finalbody"):
                sub = getattr(stmt, attr, None)
                if sub and isinstance(sub, list):
                    _collect_stmt_reads_writes(sub, reads, writes)
            # test expression
            test = getattr(stmt, "test", None)
            if test is not None:
                _collect_reads(test, reads)


# ---------------------------------------------------------------------------
# Topological sort (Kahn's algorithm)
# ---------------------------------------------------------------------------

class CombTopoSortPass:
    """Set ``ctx.rtl_comb_order`` to topologically-sorted @comb functions."""

    def run(self, ctx: SwContext) -> SwContext:
        funcs = ctx.rtl_component.comb_processes
        if not funcs:
            ctx.rtl_comb_order = []
            return ctx

        # Compute read/write sets per function
        fn_reads: List[Set[int]] = []
        fn_writes: List[Set[int]] = []
        for fn in funcs:
            r: Set[int] = set()
            w: Set[int] = set()
            _collect_stmt_reads_writes(fn.body, r, w)
            fn_reads.append(r)
            fn_writes.append(w)

        n = len(funcs)
        # Build adjacency: edge i→j means "fn i must run before fn j"
        # (fn i writes a field that fn j reads)
        in_degree = [0] * n
        adj: List[List[int]] = [[] for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                # If fn_i writes something that fn_j reads, i must come before j
                if fn_writes[i] & fn_reads[j]:
                    adj[i].append(j)
                    in_degree[j] += 1

        # Kahn's algorithm - preserve insertion order for ties
        from collections import deque
        queue = deque(i for i in range(n) if in_degree[i] == 0)
        order: List[int] = []

        while queue:
            i = queue.popleft()
            order.append(i)
            for j in adj[i]:
                in_degree[j] -= 1
                if in_degree[j] == 0:
                    queue.append(j)

        if len(order) != n:
            names = [f.name for f in funcs]
            raise ValueError(
                f"Combinational loop detected among @comb processes: {names}"
            )

        ctx.rtl_comb_order = [funcs[i] for i in order]
        return ctx

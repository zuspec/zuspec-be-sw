"""WaitPointAnalysisPass — static latency analysis for component methods.

Traverses the call graph of every component method and computes:
  - ``min_ps``: minimum accumulated wait time across all execution paths (ps)
  - ``max_ps``: maximum accumulated wait time (``sys.maxsize`` if unbounded)
  - ``has_wait``: True if the method calls ``wait()`` directly or transitively

Results are stored in ``SwContext.method_latencies`` keyed by
``(component_name, method_name)``.
"""
from __future__ import annotations

import sys
from typing import Dict, Optional, Set, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext, MethodLatency
from zuspec.be.sw.pipeline import SwPass

UNBOUNDED = sys.maxsize


class WaitPointAnalysisPass(SwPass):
    """Compute static latency bounds for all component methods.

    The pass makes a single forward pass over all ``DataTypeComponent`` types
    in the context.  For each async function it estimates minimum and maximum
    cumulative ``wait()`` time.

    Current implementation: single-pass heuristic that recognises:
    - ``await self.wait(ns(N))`` / ``await self.wait_ns(N)`` → fixed delay
    - ``while True: …wait…`` → UNBOUNDED max
    - Transitive calls to other methods (same component) with known latencies

    A future full implementation would build a complete call graph across
    components using ``SwConnection`` data.
    """

    def run(self, ctxt: SwContext) -> SwContext:
        # Process each component type
        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, ir.DataTypeComponent):
                continue
            for fn in dtype.functions:
                if not fn.is_async:
                    continue
                key = (type_name, fn.name)
                if key not in ctxt.method_latencies:
                    lat = self._analyze(fn, dtype, ctxt, visited=set())
                    ctxt.method_latencies[key] = lat
        return ctxt

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def _analyze(
        self,
        fn: ir.Function,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
        visited: Set[Tuple[str, str]],
    ) -> MethodLatency:
        """Analyse a single function, returning its ``MethodLatency``."""
        key = (comp.name or "", fn.name)
        if key in visited:
            # Recursive call — conservatively mark unbounded
            return MethodLatency(min_ps=0, max_ps=UNBOUNDED, has_wait=True)
        visited = visited | {key}

        min_ps, max_ps, has_wait = self._scan_stmts(
            fn.body, comp, ctxt, visited, in_loop=False
        )
        return MethodLatency(min_ps=min_ps, max_ps=max_ps, has_wait=has_wait)

    def _scan_stmts(
        self,
        stmts,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
        visited: Set[Tuple[str, str]],
        in_loop: bool,
    ) -> Tuple[int, int, bool]:
        """Return ``(min_ps, max_ps, has_wait)`` for a statement list."""
        total_min = 0
        total_max = 0
        has_wait = False

        for stmt in stmts:
            s_min, s_max, s_hw = self._scan_stmt(stmt, comp, ctxt, visited, in_loop)
            total_min += s_min
            if total_max == UNBOUNDED or s_max == UNBOUNDED:
                total_max = UNBOUNDED
            else:
                total_max += s_max
            has_wait = has_wait or s_hw

        return total_min, total_max, has_wait

    def _scan_stmt(
        self,
        stmt,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
        visited: Set[Tuple[str, str]],
        in_loop: bool,
    ) -> Tuple[int, int, bool]:
        """Return ``(min_ps, max_ps, has_wait)`` for a single statement."""
        # Wait call: ExprStmt(StmtExpr(ExprAwait(ExprCall(func=wait_ns/wait_ps/wait))))
        if isinstance(stmt, ir.StmtExpr):
            return self._scan_expr(stmt.expr, comp, ctxt, visited, in_loop)

        if isinstance(stmt, ir.StmtAssign):
            return self._scan_expr(stmt.value, comp, ctxt, visited, in_loop)

        # If/else: take min of branches for min; max of branches for max
        if isinstance(stmt, ir.StmtIf):
            then_min, then_max, then_hw = self._scan_stmts(
                stmt.body, comp, ctxt, visited, in_loop
            )
            else_min, else_max, else_hw = self._scan_stmts(
                getattr(stmt, "orelse", []), comp, ctxt, visited, in_loop
            )
            hw = then_hw or else_hw
            if not stmt.body:
                return else_min, else_max, hw
            if not getattr(stmt, "orelse", []):
                return 0, then_max, hw
            return min(then_min, else_min), max(then_max, else_max), hw

        # While / for loops: body may execute 0 or more times
        if isinstance(stmt, (ir.StmtWhile, ir.StmtFor)):
            body_min, body_max, body_hw = self._scan_stmts(
                stmt.body, comp, ctxt, visited, in_loop=True
            )
            # If body has a wait, loop makes max unbounded
            if body_hw:
                return 0, UNBOUNDED, True
            return 0, 0, False

        return 0, 0, False

    def _scan_expr(
        self,
        expr,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
        visited: Set[Tuple[str, str]],
        in_loop: bool,
    ) -> Tuple[int, int, bool]:
        """Return ``(min_ps, max_ps, has_wait)`` for an expression."""
        if expr is None:
            return 0, 0, False

        # Await expression — check what's being awaited
        if isinstance(expr, ir.ExprAwait):
            return self._scan_await(expr.value, comp, ctxt, visited, in_loop)

        # Traverse sub-expressions (non-exhaustive but covers common patterns)
        for attr in ("value", "func", "args"):
            child = getattr(expr, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                for c in child:
                    if hasattr(c, "__class__") and c.__class__.__name__.startswith("Expr"):
                        r = self._scan_expr(c, comp, ctxt, visited, in_loop)
                        if r[2]:
                            return r
            elif hasattr(child, "__class__") and child.__class__.__name__.startswith("Expr"):
                r = self._scan_expr(child, comp, ctxt, visited, in_loop)
                if r[2]:
                    return r

        return 0, 0, False

    def _scan_await(
        self,
        expr,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
        visited: Set[Tuple[str, str]],
        in_loop: bool,
    ) -> Tuple[int, int, bool]:
        """Analyse an expression that is the target of ``await``."""
        if not isinstance(expr, ir.ExprCall):
            return 0, 0, True  # Unknown awaitable: mark as has_wait

        # Detect wait_ns / wait_us / wait_ps / wait_cycles / wait calls
        func_name = self._call_name(expr)
        ps = self._extract_wait_ps(func_name, expr)
        if ps is not None:
            return ps, ps, True

        # Detect call to another method on self — attempt transitive analysis
        if func_name and not func_name.startswith("self.wait"):
            callee_fn = self._find_method(comp, func_name)
            if callee_fn is not None:
                lat = self._analyze(callee_fn, comp, ctxt, visited)
                return lat.min_ps, lat.max_ps, lat.has_wait

        # Unknown awaitable: conservatively mark as has_wait with unknown latency
        return 0, UNBOUNDED, True

    def _call_name(self, expr: ir.ExprCall) -> Optional[str]:
        """Extract a dotted name string from a call expression."""
        func = getattr(expr, "func", None)
        if func is None:
            return None
        if isinstance(func, ir.ExprAttribute):
            base_name = self._call_name_from_expr(getattr(func, "value", None))
            return f"{base_name}.{func.attr}" if base_name else func.attr
        if isinstance(func, (ir.ExprRefLocal, ir.ExprRefUnresolved)):
            return func.name
        return None

    def _call_name_from_expr(self, expr) -> Optional[str]:
        if expr is None:
            return None
        if isinstance(expr, ir.ExprAttribute):
            base = self._call_name_from_expr(getattr(expr, "value", None))
            return f"{base}.{expr.attr}" if base else expr.attr
        if isinstance(expr, (ir.ExprRefLocal, ir.ExprRefUnresolved)):
            return expr.name
        if isinstance(expr, ir.TypeExprRefSelf):
            return "self"
        return None

    def _extract_wait_ps(self, func_name: Optional[str], call: ir.ExprCall) -> Optional[int]:
        """If *call* is a wait helper, return the delay in picoseconds, else None."""
        if func_name is None:
            return None
        name = func_name.split(".")[-1]
        # Try to extract the literal argument value
        args = getattr(call, "args", []) or []
        val = self._literal_int(args[0]) if args else None

        if name == "wait_ps" and val is not None:
            return val
        if name == "wait_ns" and val is not None:
            return val * 1_000
        if name == "wait_us" and val is not None:
            return val * 1_000_000
        if name == "wait_ms" and val is not None:
            return val * 1_000_000_000
        if name in ("wait", "wait_cycles"):
            # Cannot determine ps without knowing clock period
            return None
        # Helper: ns(N), us(N), ps(N) helper functions
        if name in ("ns",) and val is not None:
            return val * 1_000
        if name in ("us",) and val is not None:
            return val * 1_000_000
        if name in ("ps",) and val is not None:
            return val
        return None

    def _literal_int(self, expr) -> Optional[int]:
        """Extract a literal integer from an expression node, or None."""
        if isinstance(expr, ir.ExprConstant):
            v = getattr(expr, "value", None)
            if isinstance(v, int):
                return v
        if isinstance(expr, ir.ExprCall):
            # Handle ns(N), us(N), ps(N)
            inner_args = getattr(expr, "args", []) or []
            if inner_args:
                return self._literal_int(inner_args[0])
        return None

    def _find_method(self, comp: ir.DataTypeComponent, name: str) -> Optional[ir.Function]:
        """Find a method by bare name on a component."""
        bare = name.split(".")[-1]
        for fn in comp.functions:
            if fn.name == bare:
                return fn
        return None

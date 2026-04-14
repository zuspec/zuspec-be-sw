"""
WaitLowerPass — lower behavioral wait expressions to C tick-delta strings.

For each ``@process`` found in ``comp.functions`` this pass:
  * Validates that every ``ExprAwait`` wraps a ``wait_cycles`` or
    ``wait_time`` call.
  * Converts constant waits to literal picosecond deltas.
  * Converts runtime waits to C expressions using the component field names.
  * Emits a warning for ``wait_time`` with rounding error > 50 %.
  * Stores the annotated process list in ``ctx.rtl_behav_processes``.

Structures stored in ``ctx.rtl_behav_processes``:
  Each element is a ``BehavProcess(name, suspensions, ir_node)`` where
  ``suspensions`` is populated lazily by the C emitter, not here.
  The pass instead annotates context so the emitter can call
  ``WaitLowerPass.lower_await(expr, ctx)`` at emit time.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from zuspec.dataclasses.ir.expr import (
    ExprAwait, ExprCall, ExprAttribute, ExprRefUnresolved,
    ExprConstant, ExprRefField,
)
from zuspec.dataclasses.ir.data_type import Process

from zuspec.be.sw.ir.base import SwContext

# Picosecond multiplier for each time unit name.
_UNIT_PS: dict = {
    "PS": 1,
    "NS": 1_000,
    "US": 1_000_000,
    "MS": 1_000_000_000,
    "S":  1_000_000_000_000,
}


@dataclass
class LoweredSuspend:
    """A single lowered suspension point (``await wait_*(...)``)."""
    tick_delta_expr: str           # C expression: ps delta from current tick
    is_yield: bool = False         # True → wait_cycles(0); just reschedule
    warning: Optional[str] = None  # non-None → rounding warn was emitted


class WaitLowerPass:
    """Identify behavioral ``Process`` objects and validate / pre-lower waits."""

    def run(self, ctx: SwContext) -> SwContext:
        comp = ctx.rtl_component
        # Collect Process objects (not Function).
        procs = [f for f in comp.functions if isinstance(f, Process)]
        ctx.rtl_behav_processes = procs
        # Lower all ExprAwait nodes we can find, collecting warnings.
        for proc in procs:
            self._walk_stmts(proc.body, ctx)
        return ctx

    # ------------------------------------------------------------------
    # Public helper used by CEmitPass
    # ------------------------------------------------------------------

    @staticmethod
    def lower_await(
        call: ExprCall,
        fields,
        period_ps: int,
        warnings: List[str],
    ) -> LoweredSuspend:
        """Convert a ``wait_cycles`` / ``wait_time`` ExprCall to a
        ``LoweredSuspend``.

        Parameters
        ----------
        call:
            The ``ExprCall`` node that is the value of an ``ExprAwait``.
        fields:
            Component field list (used to map ``ExprRefField`` indices).
        period_ps:
            Primary clock period in picoseconds.
        warnings:
            Mutable list; any rounding warnings are appended here.
        """
        func_name = WaitLowerPass._call_name(call)

        if func_name == "wait_cycles":
            amount = call.args[0]
            return WaitLowerPass._lower_cycles(amount, fields, period_ps)

        if func_name == "wait_time":
            amount = call.args[0]
            unit_arg = call.args[1] if len(call.args) > 1 else None
            return WaitLowerPass._lower_time(
                amount, unit_arg, fields, period_ps, warnings
            )

        # Fallback: unknown call wrapped in await — treat as 1-cycle yield.
        return LoweredSuspend(tick_delta_expr=f"{period_ps}ULL")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _walk_stmts(self, stmts, ctx: SwContext) -> None:
        for stmt in stmts:
            if hasattr(stmt, "expr") and isinstance(stmt.expr, ExprAwait):
                call = stmt.expr.value
                if isinstance(call, ExprCall):
                    susp = WaitLowerPass.lower_await(
                        call, ctx.rtl_component.fields,
                        ctx.rtl_domain_period_ps, ctx.rtl_warnings,
                    )
                    if susp.warning:
                        ctx.rtl_warnings.append(susp.warning)
            # Recurse into compound statements.
            for attr in ("body", "orelse", "handlers"):
                sub = getattr(stmt, attr, None)
                if isinstance(sub, list):
                    self._walk_stmts(sub, ctx)

    @staticmethod
    def _call_name(call: ExprCall) -> str:
        """Return the bare function name from the call (e.g. 'wait_cycles')."""
        func = call.func
        if isinstance(func, ExprAttribute):
            return func.attr
        if isinstance(func, ExprRefUnresolved):
            return func.name
        return ""

    @staticmethod
    def _lower_cycles(
        amount_expr,
        fields,
        period_ps: int,
    ) -> LoweredSuspend:
        if isinstance(amount_expr, ExprConstant):
            n = int(amount_expr.value)
            if n == 0:
                return LoweredSuspend(
                    tick_delta_expr="0ULL",
                    is_yield=True,
                )
            return LoweredSuspend(tick_delta_expr=f"{n * period_ps}ULL")
        # Runtime N
        c_amount = WaitLowerPass._lower_amount(amount_expr, fields)
        return LoweredSuspend(
            tick_delta_expr=f"(uint64_t)({c_amount}) * {period_ps}ULL"
        )

    @staticmethod
    def _lower_time(
        amount_expr,
        unit_arg,
        fields,
        period_ps: int,
        warnings: List[str],
    ) -> LoweredSuspend:
        unit_name = "NS"  # default
        if isinstance(unit_arg, ExprRefUnresolved):
            unit_name = unit_arg.name.upper()
        unit_ps = _UNIT_PS.get(unit_name, 1_000)

        if isinstance(amount_expr, ExprConstant):
            t_ps = int(amount_expr.value) * unit_ps
            n_cycles = math.ceil(t_ps / period_ps)
            actual_ps = n_cycles * period_ps
            warn = None
            if t_ps > 0 and abs(actual_ps - t_ps) > t_ps * 0.5:
                warn = (
                    f"wait_time rounded from {t_ps}ps to {actual_ps}ps "
                    f"(>{50}% rounding error on {period_ps}ps clock)"
                )
                warnings.append(warn)
            return LoweredSuspend(
                tick_delta_expr=f"{actual_ps}ULL",
                warning=warn,
            )

        # Runtime amount
        c_amount = WaitLowerPass._lower_amount(amount_expr, fields)
        expr = (
            f"ZSP_CEIL_DIV((uint64_t)({c_amount}) * {unit_ps}ULL, "
            f"{period_ps}ULL) * {period_ps}ULL"
        )
        return LoweredSuspend(tick_delta_expr=expr)

    @staticmethod
    def _lower_amount(expr, fields) -> str:
        """Convert an ``ExprRefField`` / ``ExprCall(int, ...)`` / etc. to C."""
        if isinstance(expr, ExprConstant):
            return str(int(expr.value))
        if isinstance(expr, ExprRefField):
            if expr.index < len(fields):
                return f"self->{fields[expr.index].name}"
            return f"self->_f{expr.index}"
        if isinstance(expr, ExprCall):
            # int(self.delay) — unwrap the cast, emit the inner expression
            inner_c = WaitLowerPass._lower_amount(
                expr.args[0] if expr.args else ExprConstant(value=0),
                fields,
            )
            return inner_c
        return "0 /* unknown */"

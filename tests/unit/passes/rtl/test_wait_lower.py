"""
Unit tests for WaitLowerPass — tick-delta expression lowering.

Tests verify that wait_cycles(N) and wait_time(T, unit) are correctly
lowered to C ps-delta expressions for different clock periods.
"""
import pytest
from unittest.mock import MagicMock

from zuspec.dataclasses.ir.expr import (
    ExprCall, ExprAttribute, ExprRefUnresolved, ExprConstant, ExprRefField,
)
from zuspec.dataclasses.ir.base import Base
import dataclasses as dc

from zuspec.be.sw.passes.rtl.wait_lower import WaitLowerPass, LoweredSuspend


def _make_field(name: str, idx: int):
    f = MagicMock()
    f.name = name
    return f


def _cycles_call(n) -> ExprCall:
    """Build ExprCall for wait_cycles(n) where n is int or an ExprRefField."""
    if isinstance(n, int):
        arg = ExprConstant(value=n)
    else:
        arg = n
    return ExprCall(
        func=ExprAttribute(
            value=ExprRefUnresolved(name="zdc"),
            attr="wait_cycles",
        ),
        args=[arg],
        keywords=[],
    )


def _time_call(amount, unit: str) -> ExprCall:
    """Build ExprCall for wait_time(amount, unit)."""
    if isinstance(amount, int):
        amount_expr = ExprConstant(value=amount)
    else:
        amount_expr = amount
    return ExprCall(
        func=ExprAttribute(
            value=ExprRefUnresolved(name="zdc"),
            attr="wait_time",
        ),
        args=[amount_expr, ExprRefUnresolved(name=unit)],
        keywords=[],
    )


PERIOD_10NS = 10_000  # 10 ns in ps


class TestWaitCycles:
    def test_cycles_const_period_10ns(self):
        """wait_cycles(4) on 10 ns clock → literal 40000 ps delta."""
        call = _cycles_call(4)
        warns = []
        result = WaitLowerPass.lower_await(call, [], PERIOD_10NS, warns)
        assert result.tick_delta_expr == "40000ULL"
        assert not result.is_yield
        assert not warns

    def test_cycles_1_period_10ns(self):
        """wait_cycles(1) → literal 10000."""
        call = _cycles_call(1)
        result = WaitLowerPass.lower_await(call, [], PERIOD_10NS, [])
        assert result.tick_delta_expr == "10000ULL"

    def test_cycles_zero_yields(self):
        """wait_cycles(0) → is_yield=True (reschedule at same tick)."""
        call = _cycles_call(0)
        result = WaitLowerPass.lower_await(call, [], PERIOD_10NS, [])
        assert result.is_yield is True
        assert result.tick_delta_expr == "0ULL"

    def test_cycles_runtime_n(self):
        """wait_cycles(n) with runtime n → multiply expression."""
        field = _make_field("delay", 1)
        ref = ExprRefField(base=MagicMock(), index=1)
        call = _cycles_call(ref)
        result = WaitLowerPass.lower_await(call, [MagicMock(), field], PERIOD_10NS, [])
        assert "self->delay" in result.tick_delta_expr
        assert "10000" in result.tick_delta_expr
        assert not result.is_yield

    def test_cycles_int_cast_unwrapped(self):
        """wait_cycles(int(self.delay)) → unwraps int() cast."""
        field = _make_field("delay", 1)
        ref = ExprRefField(base=MagicMock(), index=1)
        int_call = ExprCall(
            func=ExprRefUnresolved(name="int"),
            args=[ref],
            keywords=[],
        )
        call = _cycles_call(int_call)
        result = WaitLowerPass.lower_await(call, [MagicMock(), field], PERIOD_10NS, [])
        assert "self->delay" in result.tick_delta_expr


class TestWaitTime:
    def test_realtime_exact(self):
        """wait_time(100, NS) on 10 ns clock → 100000 ps (exact)."""
        call = _time_call(100, "NS")
        warns = []
        result = WaitLowerPass.lower_await(call, [], PERIOD_10NS, warns)
        assert result.tick_delta_expr == "100000ULL"
        assert not warns

    def test_realtime_ceiling(self):
        """wait_time(95, NS) on 10 ns clock → rounds up to 100000 ps."""
        call = _time_call(95, "NS")
        warns = []
        result = WaitLowerPass.lower_await(call, [], PERIOD_10NS, warns)
        assert result.tick_delta_expr == "100000ULL"
        assert not warns  # 5ns rounding on 100ns ≤ 50%

    def test_diagnostic_large_rounding(self):
        """wait_time(3, NS) on 7 ns clock → >50% rounding error → warning."""
        call = _time_call(3, "NS")
        warns = []
        result = WaitLowerPass.lower_await(call, [], 7_000, warns)
        # 3ns → ceil(3000/7000)=1 cycle → 7000 ps (rounds up from 3000 to 7000)
        assert result.tick_delta_expr == "7000ULL"
        # Warning should mention the rounding
        assert len(warns) == 1
        assert "rounded" in warns[0].lower()

    def test_realtime_runtime_amount(self):
        """wait_time(t_reg, NS) with runtime t → ZSP_CEIL_DIV expression."""
        field = _make_field("delay_reg", 1)
        ref = ExprRefField(base=MagicMock(), index=1)
        call = _time_call(ref, "NS")
        result = WaitLowerPass.lower_await(call, [MagicMock(), field], PERIOD_10NS, [])
        assert "ZSP_CEIL_DIV" in result.tick_delta_expr
        assert "self->delay_reg" in result.tick_delta_expr

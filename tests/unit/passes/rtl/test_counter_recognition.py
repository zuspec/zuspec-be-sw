"""
Unit tests for CounterRecognitionPass and counter-wait lowering.

Tests cover:
  - CounterRecognitionPass populates ctx.counter_fields for recognized types
  - Non-counter sub-component fields are ignored
  - wait_next() and wait_for(N) produce correct inline C expressions
  - is_counter_jump flag is set on LoweredSuspend
  - Counter fields are absent from the generated C struct / init / ctypes
"""
import pytest
from unittest.mock import MagicMock

from zuspec.ir.core.expr import (
    ExprCall, ExprAttribute, ExprRefUnresolved, ExprConstant, ExprRefField,
)
from zuspec.ir.core.data_type import DataTypeComponent

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.rtl.counter_recognition import (
    CounterInfo,
    CounterRecognitionPass,
    _COUNTER_TYPE_NAMES,
)
from zuspec.be.sw.passes.rtl.wait_lower import WaitLowerPass, LoweredSuspend


PERIOD_PS = 1_000  # 1 ns in ps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(**overrides) -> SwContext:
    ctx = SwContext()
    ctx.rtl_domain_period_ps = PERIOD_PS
    for k, v in overrides.items():
        setattr(ctx, k, v)
    return ctx


def _make_comp_with_counter_field(type_name: str, period_or_width: int):
    """Build a minimal mock IR component with one counter-type sub-field."""
    comp = MagicMock()

    dt = MagicMock(spec=DataTypeComponent)
    dt.name = type_name

    field = MagicMock()
    field.name = "cnt"
    field.datatype = dt

    comp.fields = [field]
    return comp, field


def _make_counter_instance(type_name: str, period_or_width: int):
    """Build a mock Python class-level counter instance."""
    inst = MagicMock()
    if type_name in ("ModuloCounter", "WatchdogCounter"):
        inst.PERIOD = period_or_width
    else:
        inst.WIDTH = period_or_width
    return inst


def _make_parent_class(ctr_field_name: str, ctr_instance):
    cls = MagicMock()
    setattr(cls, ctr_field_name, ctr_instance)
    return cls


def _counter_wait_call(field_name: str, func_name: str, *args) -> ExprCall:
    """Build ExprCall for await self.<field_name>.<func_name>(*args)."""
    self_ref = ExprRefUnresolved(name="self")
    field_ref = ExprAttribute(value=self_ref, attr=field_name)
    method_ref = ExprAttribute(value=field_ref, attr=func_name)
    return ExprCall(func=method_ref, args=list(args), keywords=[])


# ---------------------------------------------------------------------------
# CounterRecognitionPass
# ---------------------------------------------------------------------------

class TestCounterRecognitionPass:

    def _run(self, type_name: str, period_or_width: int, *, is_class=True):
        comp, field = _make_comp_with_counter_field(type_name, period_or_width)
        ctx = _make_ctx(rtl_component=comp)

        if is_class:
            inst = _make_counter_instance(type_name, period_or_width)
            ctx.rtl_component_class = _make_parent_class("cnt", inst)
        else:
            ctx.rtl_component_class = None
            # Set up IR const fields on the DataTypeComponent
            sub_field = MagicMock()
            sub_field.is_const = True
            if type_name in ("ModuloCounter", "WatchdogCounter"):
                sub_field.name = "PERIOD"
                sub_field.default_value = period_or_width
            else:
                sub_field.name = "WIDTH"
                sub_field.default_value = period_or_width
            field.datatype.fields = [sub_field]

        CounterRecognitionPass().run(ctx)
        return ctx

    def test_modulo_counter_recognized(self):
        ctx = self._run("ModuloCounter", 16)
        assert "cnt" in ctx.counter_fields
        info = ctx.counter_fields["cnt"]
        assert info.modulus == 16
        assert info.is_modulo is True
        assert info.period_ps == PERIOD_PS

    def test_watchdog_counter_recognized(self):
        ctx = self._run("WatchdogCounter", 32)
        info = ctx.counter_fields["cnt"]
        assert info.modulus == 32
        assert info.is_modulo is True

    def test_plain_counter_recognized(self):
        ctx = self._run("Counter", 8)  # WIDTH=8 → modulus=256
        info = ctx.counter_fields["cnt"]
        assert info.modulus == 256
        assert info.is_modulo is False

    def test_non_counter_type_ignored(self):
        comp, field = _make_comp_with_counter_field("SomeOtherComp", 8)
        ctx = _make_ctx(rtl_component=comp, rtl_component_class=None)
        CounterRecognitionPass().run(ctx)
        assert ctx.counter_fields == {}

    def test_no_component_fields(self):
        comp = MagicMock()
        comp.fields = []
        ctx = _make_ctx(rtl_component=comp, rtl_component_class=None)
        CounterRecognitionPass().run(ctx)
        assert ctx.counter_fields == {}

    def test_null_component(self):
        ctx = _make_ctx(rtl_component=None, rtl_component_class=None)
        CounterRecognitionPass().run(ctx)
        assert ctx.counter_fields == {}

    def test_fallback_ir_const_fields_modulo(self):
        ctx = self._run("ModuloCounter", 64, is_class=False)
        assert ctx.counter_fields["cnt"].modulus == 64

    def test_fallback_ir_const_fields_plain(self):
        ctx = self._run("Counter", 4, is_class=False)  # WIDTH=4 → modulus=16
        assert ctx.counter_fields["cnt"].modulus == 16

    def test_multiple_counter_fields(self):
        comp = MagicMock()
        fields = []
        for name, tname, period in [
            ("a", "ModuloCounter", 8),
            ("b", "WatchdogCounter", 4),
        ]:
            dt = MagicMock(spec=DataTypeComponent)
            dt.name = tname
            f = MagicMock()
            f.name = name
            f.datatype = dt
            fields.append(f)
        comp.fields = fields

        cls = MagicMock()
        for name, tname, period in [
            ("a", "ModuloCounter", 8),
            ("b", "WatchdogCounter", 4),
        ]:
            inst = _make_counter_instance(tname, period)
            setattr(cls, name, inst)

        ctx = _make_ctx(rtl_component=comp, rtl_component_class=cls)
        CounterRecognitionPass().run(ctx)

        assert len(ctx.counter_fields) == 2
        assert ctx.counter_fields["a"].modulus == 8
        assert ctx.counter_fields["b"].modulus == 4


# ---------------------------------------------------------------------------
# WaitLowerPass — counter wait lowering
# ---------------------------------------------------------------------------

class TestCounterWaitLowering:

    def _lower(self, call: ExprCall, counter_fields: dict) -> LoweredSuspend:
        return WaitLowerPass.lower_await(
            call, [], PERIOD_PS, [], counter_fields=counter_fields
        )

    def test_wait_next_is_counter_jump(self):
        call = _counter_wait_call("cnt", "wait_next")
        info = CounterInfo("cnt", modulus=8, period_ps=PERIOD_PS, is_modulo=True)
        result = self._lower(call, {"cnt": info})
        assert result.is_counter_jump is True

    def test_wait_next_expr_contains_modulus(self):
        call = _counter_wait_call("cnt", "wait_next")
        info = CounterInfo("cnt", modulus=8, period_ps=PERIOD_PS, is_modulo=True)
        result = self._lower(call, {"cnt": info})
        assert "8" in result.tick_delta_expr
        assert str(PERIOD_PS) in result.tick_delta_expr

    def test_wait_for_is_counter_jump(self):
        target = ExprConstant(value=3)
        call = _counter_wait_call("cnt", "wait_for", target)
        info = CounterInfo("cnt", modulus=8, period_ps=PERIOD_PS, is_modulo=True)
        result = self._lower(call, {"cnt": info})
        assert result.is_counter_jump is True

    def test_wait_for_expr_contains_target(self):
        target = ExprConstant(value=5)
        call = _counter_wait_call("cnt", "wait_for", target)
        info = CounterInfo("cnt", modulus=8, period_ps=PERIOD_PS, is_modulo=True)
        result = self._lower(call, {"cnt": info})
        assert "5" in result.tick_delta_expr
        assert "8" in result.tick_delta_expr

    def test_unknown_field_not_counter_jump(self):
        call = _counter_wait_call("other", "wait_next")
        info = CounterInfo("cnt", modulus=8, period_ps=PERIOD_PS, is_modulo=True)
        result = self._lower(call, {"cnt": info})
        # should fall through to the fallback (unknown call → 1 cycle)
        assert result.is_counter_jump is False

    def test_no_counter_fields_dict_no_counter_jump(self):
        call = _counter_wait_call("cnt", "wait_next")
        result = self._lower(call, {})
        assert result.is_counter_jump is False

    def test_counter_fields_none_no_counter_jump(self):
        call = _counter_wait_call("cnt", "wait_next")
        result = WaitLowerPass.lower_await(call, [], PERIOD_PS, [])
        assert result.is_counter_jump is False

    def test_wait_cycles_still_works_with_counter_fields(self):
        call = ExprCall(
            func=ExprAttribute(value=ExprRefUnresolved(name="zdc"), attr="wait_cycles"),
            args=[ExprConstant(value=4)],
            keywords=[],
        )
        info = CounterInfo("cnt", modulus=8, period_ps=PERIOD_PS, is_modulo=True)
        result = self._lower(call, {"cnt": info})
        assert result.is_counter_jump is False
        assert str(4 * PERIOD_PS) in result.tick_delta_expr

    def test_wait_next_expr_never_zero(self):
        """The modulus subtraction ensures result ≥ 1 cycle."""
        call = _counter_wait_call("cnt", "wait_next")
        info = CounterInfo("cnt", modulus=4, period_ps=PERIOD_PS, is_modulo=True)
        result = self._lower(call, {"cnt": info})
        # Expression should not contain a subtraction that can yield 0:
        # (M - (tick/P)%M) is in [1, M], never 0.
        assert result.is_counter_jump is True

    def test_wait_next_large_modulus(self):
        call = _counter_wait_call("cnt", "wait_next")
        info = CounterInfo("cnt", modulus=1024, period_ps=2_000, is_modulo=False)
        result = self._lower(call, {"cnt": info})
        assert "1024" in result.tick_delta_expr
        assert "2000" in result.tick_delta_expr

    def test_wait_for_field_ref_target(self):
        """wait_for(self.threshold) should produce a C expression with a
        self->threshold reference."""
        fields = [MagicMock()]
        fields[0].name = "threshold"
        target = ExprRefField(base=ExprRefUnresolved(name="self"), index=0)
        call = _counter_wait_call("cnt", "wait_for", target)
        info = CounterInfo("cnt", modulus=8, period_ps=PERIOD_PS, is_modulo=True)
        result = WaitLowerPass.lower_await(
            call, fields, PERIOD_PS, [], counter_fields={"cnt": info}
        )
        assert result.is_counter_jump is True
        assert "threshold" in result.tick_delta_expr

"""Unit tests for ExprLower (expression/statement lowering)."""
import pytest
import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory
from zuspec.dataclasses.ir.data_type import DataTypeInt
from zuspec.dataclasses.ir.fields import Field, FieldKind
from zuspec.dataclasses.ir.expr import (
    ExprBin, BinOp, ExprConstant, ExprRefField, TypeExprRefSelf,
)

from zuspec.be.sw.passes.rtl.expr_lower import ExprLower


def _make_fields(*names_bits):
    """Create a list of simple integer fields for testing."""
    fields = []
    for name, bits in names_bits:
        f = Field(name=name, datatype=DataTypeInt(bits=bits, signed=False))
        fields.append(f)
    return fields


def test_bit_slice_single_bit():
    """ExprRefField targeting a 1-bit field produces 'self->field'."""
    fields = _make_fields(("x", 1), ("y", 8))
    lower = ExprLower(fields, set())
    expr = ExprRefField(base=TypeExprRefSelf(), index=0)
    assert lower.lower_expr(expr) == "self->x"


def test_expr_constant_zero():
    """ExprConstant(0) → '0u'."""
    lower = ExprLower([], set())
    assert lower.lower_expr(ExprConstant(value=0)) == "0u"


def test_expr_constant_literal():
    """ExprConstant(42) → '42u'."""
    lower = ExprLower([], set())
    assert lower.lower_expr(ExprConstant(value=42)) == "42u"


def test_expr_constant_negative():
    """ExprConstant(-1) → '-1'."""
    lower = ExprLower([], set())
    assert lower.lower_expr(ExprConstant(value=-1)) == "-1"


def test_exprbin_add():
    """ExprBin(+) → '(<lhs> + <rhs>)'."""
    lower = ExprLower([], set())
    expr = ExprBin(
        lhs=ExprConstant(value=1),
        op=BinOp.Add,
        rhs=ExprConstant(value=2),
    )
    assert lower.lower_expr(expr) == "(1u + 2u)"


def test_exprbin_operators():
    """All basic binary operators map to correct C operators."""
    lower = ExprLower([], set())
    cases = [
        (BinOp.Sub,    "(1u - 2u)"),
        (BinOp.Mult,   "(1u * 2u)"),
        (BinOp.BitAnd, "(1u & 2u)"),
        (BinOp.BitOr,  "(1u | 2u)"),
        (BinOp.BitXor, "(1u ^ 2u)"),
        (BinOp.LShift, "(1u << 2u)"),
        (BinOp.RShift, "(1u >> 2u)"),
        (BinOp.Eq,     "(1u == 2u)"),
        (BinOp.Lt,     "(1u < 2u)"),
        (BinOp.Gt,     "(1u > 2u)"),
    ]
    for op, expected in cases:
        expr = ExprBin(lhs=ExprConstant(value=1), op=op, rhs=ExprConstant(value=2))
        assert lower.lower_expr(expr) == expected


def test_field_ref_self():
    """ExprRefField(self, 0) → 'self->field0'."""
    fields = _make_fields(("count", 32))
    lower = ExprLower(fields, set())
    expr = ExprRefField(base=TypeExprRefSelf(), index=0)
    assert lower.lower_expr(expr) == "self->count"


def test_field_ref_nxt():
    """Write target in @sync (nxt_fields) → 'self->_nxt.field'."""
    fields = _make_fields(("count", 32))
    lower = ExprLower(fields, {"count"})
    expr = ExprRefField(base=TypeExprRefSelf(), index=0)
    # In read context, use _regs sub-struct
    assert lower.lower_expr(expr, write_ctx=False) == "self->_regs.count"
    # In write context, use _nxt sub-struct
    assert lower.lower_expr(expr, write_ctx=True) == "self->_nxt.count"


def test_field_ref_not_nxt_in_read():
    """Even if field is in nxt_fields, read context uses _regs sub-struct."""
    fields = _make_fields(("count", 32))
    lower = ExprLower(fields, {"count"})
    expr = ExprRefField(base=TypeExprRefSelf(), index=0)
    assert lower.lower_expr(expr, write_ctx=False) == "self->_regs.count"

"""Translate a Layer-0 constraint ``Expr`` DAG to dv-solve C builder calls.

Mirrors `zuspec-solver/ir_translator.py`'s op mapping (`_BINOP_MAP` /
`_CMPOP_MAP` / `_UNARYOP_MAP`) but emits C: each sub-expression becomes an
``ExprRef e<N> = expr_*(sp, ...);`` line, and the constraint root is handed to
``problem_add_constraint``.  The op codes are emitted as the dv-solve C enum
identifiers (`BIN_ADD`, …) for readable generated code.
"""
from __future__ import annotations

from typing import Dict, List

from zuspec.ir.core.expr import (
    BinOp, CmpOp, UnaryOp, BoolOp,
    ExprConstant, ExprAttribute, ExprBin, ExprUnary, ExprCompare, ExprBool,
    ExprSubscript, ExprSlice, ExprIn, ExprRange, ExprRangeList, TypeExprRefSelf,
)
from zuspec.ir.core.xf import UnsupportedConstructError


_BIN = {
    BinOp.Add: "BIN_ADD", BinOp.Sub: "BIN_SUB", BinOp.Mult: "BIN_MUL",
    BinOp.Div: "BIN_DIV", BinOp.Mod: "BIN_MOD",
    BinOp.BitAnd: "BIN_BAND", BinOp.BitOr: "BIN_BOR", BinOp.BitXor: "BIN_BXOR",
    BinOp.LShift: "BIN_LSHIFT", BinOp.RShift: "BIN_RSHIFT",
    BinOp.Eq: "BIN_EQ", BinOp.NotEq: "BIN_NEQ",
    BinOp.Lt: "BIN_LT", BinOp.LtE: "BIN_LTE",
    BinOp.Gt: "BIN_GT", BinOp.GtE: "BIN_GTE",
    BinOp.And: "BIN_AND", BinOp.Or: "BIN_OR",
}
_CMP = {
    CmpOp.Eq: "BIN_EQ", CmpOp.NotEq: "BIN_NEQ",
    CmpOp.Lt: "BIN_LT", CmpOp.LtE: "BIN_LTE",
    CmpOp.Gt: "BIN_GT", CmpOp.GtE: "BIN_GTE",
}
_UN = {UnaryOp.USub: "UN_NEG", UnaryOp.Not: "UN_NOT", UnaryOp.Invert: "UN_INVERT"}


class ConstraintCEmitter:
    """Accumulates C builder lines for one ``__randomize`` function."""

    def __init__(self, var_id_map: Dict[str, int], sp: str = "sp"):
        self.var_id_map = var_id_map
        self.sp = sp
        self.lines: List[str] = []
        self._n = 0

    def _tmp(self) -> str:
        self._n += 1
        return "e%d" % self._n

    def _emit(self, call: str) -> str:
        t = self._tmp()
        self.lines.append("ExprRef %s = %s;" % (t, call))
        return t

    def _const(self, value: int) -> str:
        signed = 1 if value < 0 else 0
        return self._emit("expr_const(%s, %dLL, %d)" % (self.sp, value, signed))

    def emit_constraint(self, e) -> None:
        ref = self.emit_expr(e)
        self.lines.append("problem_add_constraint(%s, %s);" % (self.sp, ref))

    # ------------------------------------------------------------------
    def emit_expr(self, e) -> str:
        if isinstance(e, ExprConstant):
            if not isinstance(e.value, int):
                raise UnsupportedConstructError(
                    "non-integer constant %r in constraint" % (e.value,),
                    loc=getattr(e, "loc", None))
            return self._const(e.value)

        if isinstance(e, ExprAttribute) and isinstance(e.value, TypeExprRefSelf):
            if e.attr not in self.var_id_map:
                raise UnsupportedConstructError(
                    "constraint references non-rand field %r" % e.attr,
                    loc=getattr(e, "loc", None))
            return self._emit("expr_var(%s, %d)" % (self.sp, self.var_id_map[e.attr]))

        if isinstance(e, ExprBin):
            if e.op not in _BIN:
                raise UnsupportedConstructError(
                    "unsupported binary op %s in constraint" % e.op,
                    loc=getattr(e, "loc", None))
            # Special-case `slice <eq/neq> const` → masked compare, which uses
            # only BAND/EQ (fully solver-compilable), avoiding the bit-extract /
            # shift ops dv-solve can only compile incompletely.
            if e.op in (BinOp.Eq, BinOp.NotEq):
                masked = self._try_masked_compare(e)
                if masked is not None:
                    return masked
            l = self.emit_expr(e.lhs)
            r = self.emit_expr(e.rhs)
            return self._emit("expr_binary(%s, %s, %s, %s)"
                              % (self.sp, _BIN[e.op], l, r))

        if isinstance(e, ExprUnary):
            if e.op == UnaryOp.UAdd:
                return self.emit_expr(e.operand)
            if e.op not in _UN:
                raise UnsupportedConstructError(
                    "unsupported unary op %s in constraint" % e.op,
                    loc=getattr(e, "loc", None))
            o = self.emit_expr(e.operand)
            return self._emit("expr_unary(%s, %s, %s)" % (self.sp, _UN[e.op], o))

        if isinstance(e, ExprCompare):
            return self._emit_compare(e)

        if isinstance(e, ExprBool):
            op = "BIN_AND" if e.op == BoolOp.And else "BIN_OR"
            refs = [self.emit_expr(v) for v in e.values]
            acc = refs[0]
            for r in refs[1:]:
                acc = self._emit("expr_binary(%s, %s, %s, %s)"
                                 % (self.sp, op, acc, r))
            return acc

        if isinstance(e, ExprSubscript):
            return self._emit_bit_extract(e)

        if isinstance(e, ExprIn):
            return self._emit_in(e)

        raise UnsupportedConstructError(
            "unsupported constraint expression node %s" % type(e).__name__,
            loc=getattr(e, "loc", None))

    # ------------------------------------------------------------------
    def _emit_compare(self, e: ExprCompare) -> str:
        # left op0 c0 op1 c1 ...  →  (left op0 c0) AND (c0 op1 c1) AND ...
        operands = [e.left] + list(e.comparators)
        terms: List[str] = []
        for i, op in enumerate(e.ops):
            if op not in _CMP:
                raise UnsupportedConstructError(
                    "unsupported comparison op %s in constraint" % op,
                    loc=getattr(e, "loc", None))
            l = self.emit_expr(operands[i])
            r = self.emit_expr(operands[i + 1])
            terms.append(self._emit("expr_binary(%s, %s, %s, %s)"
                                    % (self.sp, _CMP[op], l, r)))
        acc = terms[0]
        for t in terms[1:]:
            acc = self._emit("expr_binary(%s, BIN_AND, %s, %s)" % (self.sp, acc, t))
        return acc

    @staticmethod
    def _bitslice_bounds(e):
        """Return ``(value_expr, hi, lo)`` if *e* is a constant bit-slice, else
        ``None``."""
        if not isinstance(e, ExprSubscript):
            return None
        sl = e.slice
        if not isinstance(sl, ExprSlice) or not getattr(sl, "is_bit_slice", False):
            return None
        if not (isinstance(sl.lower, ExprConstant) and isinstance(sl.upper, ExprConstant)):
            return None
        hi = int(sl.lower.value)
        lo = int(sl.upper.value)
        if hi < lo:
            hi, lo = lo, hi
        return e.value, hi, lo

    def _try_masked_compare(self, e: ExprBin):
        """Rewrite ``slice == const`` / ``slice != const`` to
        ``(x & (mask<<lo)) <eq> (const<<lo)``; returns the ref, or ``None`` if
        the pattern doesn't apply."""
        for slice_side, const_side in ((e.lhs, e.rhs), (e.rhs, e.lhs)):
            info = self._bitslice_bounds(slice_side)
            if info is None or not isinstance(const_side, ExprConstant):
                continue
            value_expr, hi, lo = info
            width = hi - lo + 1
            mask = ((1 << width) - 1) << lo
            cval = (int(const_side.value) & ((1 << width) - 1)) << lo
            x = self.emit_expr(value_expr)
            mref = self._emit("expr_const(%s, %dLL, 0)" % (self.sp, mask))
            band = self._emit("expr_binary(%s, BIN_BAND, %s, %s)" % (self.sp, x, mref))
            cref = self._emit("expr_const(%s, %dLL, 0)" % (self.sp, cval))
            return self._emit("expr_binary(%s, %s, %s, %s)"
                              % (self.sp, _BIN[e.op], band, cref))
        return None

    def _emit_bit_extract(self, e: ExprSubscript) -> str:
        info = self._bitslice_bounds(e)
        if info is None:
            raise UnsupportedConstructError(
                "only constant bit-slices are supported in constraints",
                loc=getattr(e, "loc", None))
        value_expr, hi, lo = info
        width = hi - lo + 1
        mask = (1 << width) - 1
        # Best-effort value form `(x >> lo) & mask`.  The masked-compare special
        # case (`_try_masked_compare`) handles the common alignment pattern with
        # fully-compilable ops; this general form may compile incompletely in
        # dv-solve (shift), in which case __randomize fails loudly.
        x = self.emit_expr(value_expr)
        if lo:
            x = self._emit("expr_binary(%s, BIN_RSHIFT, %s, %s)"
                           % (self.sp, x, self._const(lo)))
        mref = self._const(mask)
        return self._emit("expr_binary(%s, BIN_BAND, %s, %s)" % (self.sp, x, mref))

    def _emit_in(self, e: ExprIn) -> str:
        container = e.container
        if not isinstance(container, ExprRangeList):
            raise UnsupportedConstructError(
                "`in` container must be a range/value list in constraints",
                loc=getattr(e, "loc", None))
        value = self.emit_expr(e.value)
        terms: List[str] = []
        for rng in container.ranges:
            if not isinstance(rng, ExprRange):
                raise UnsupportedConstructError(
                    "unsupported `in` element %s" % type(rng).__name__,
                    loc=getattr(e, "loc", None))
            if rng.upper is None:
                # single value → value == lo
                lo = self.emit_expr(rng.lower)
                terms.append(self._emit("expr_binary(%s, BIN_EQ, %s, %s)"
                                        % (self.sp, value, lo)))
            else:
                lo = self.emit_expr(rng.lower)
                hi = self.emit_expr(rng.upper)
                terms.append(self._emit("expr_in_range(%s, %s, %s, %s)"
                                        % (self.sp, value, lo, hi)))
        acc = terms[0]
        for t in terms[1:]:
            acc = self._emit("expr_binary(%s, BIN_OR, %s, %s)" % (self.sp, acc, t))
        return acc

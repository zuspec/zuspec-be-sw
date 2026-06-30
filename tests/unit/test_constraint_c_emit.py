"""Unit tests for ConstraintCEmitter — structured Constraint IR -> dv-solve C.

Companion to be-sv's ``test_constraint_emit.py``: both backends consume the
same ``zuspec.ir.core`` Constraint IR. Here we check the dv-solve C builder
output for the *hard* (solution-set-affecting) forms the flat solver model
supports, the safe no-op for ``solve before``, and the explicit errors for
distribution / array forms it cannot honor.
"""
import pytest

import zuspec.ir.core as ir
from zuspec.ir.core.xf import UnsupportedConstructError
from zuspec.be.sw.scenario.constraint_c import ConstraintCEmitter


# field-name -> solver var-id used across the corpus
_VARS = {"a": 0, "b": 1, "c": 2, "mode": 3, "addr": 4, "size": 5, "kind": 6}


def _self(name):
    return ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr=name)


def _c(v):
    return ir.ExprConstant(value=v)


def _bin(lhs, op, rhs):
    return ir.ExprBin(lhs=lhs, op=op, rhs=rhs)


def _emit(items):
    cc = ConstraintCEmitter(_VARS, sp="sp")
    for it in items:
        cc.emit_constraint(it)
    return cc.lines


def _text(items):
    return "\n".join(_emit(items))


def test_expr():
    # a == 0  ->  var(0), const(0), binary(EQ), add
    lines = _emit([ir.ConstraintExpr(expr=_bin(_self("a"), ir.BinOp.Eq, _c(0)))])
    assert lines == [
        "ExprRef e1 = expr_var(sp, 0);",
        "ExprRef e2 = expr_const(sp, 0LL, 0);",
        "ExprRef e3 = expr_binary(sp, BIN_EQ, e1, e2);",
        "problem_add_constraint(sp, e3);",
    ]


def test_implies_expr_body():
    # (mode == 1) -> (addr > 0 && addr < 16)   ==   !ant || (t1 && t2)
    item = ir.ConstraintImplies(
        antecedent=_bin(_self("mode"), ir.BinOp.Eq, _c(1)),
        body=[
            ir.ConstraintExpr(expr=_bin(_self("addr"), ir.BinOp.Gt, _c(0))),
            ir.ConstraintExpr(expr=_bin(_self("addr"), ir.BinOp.Lt, _c(16))),
        ])
    t = _text([item])
    assert "expr_unary(sp, UN_NOT," in t          # negated antecedent
    assert "BIN_AND" in t                          # body conjunction
    assert "expr_binary(sp, BIN_OR," in t          # implication
    # exactly one constraint added
    assert t.count("problem_add_constraint(sp,") == 1


def test_if_else():
    # (kind == 2) ? size == 4 : size == 8  ->  two implications, AND'd, one add
    item = ir.ConstraintIfElse(
        cond=_bin(_self("kind"), ir.BinOp.Eq, _c(2)),
        then_body=[ir.ConstraintExpr(expr=_bin(_self("size"), ir.BinOp.Eq, _c(4)))],
        else_body=[ir.ConstraintExpr(expr=_bin(_self("size"), ir.BinOp.Eq, _c(8)))])
    t = _text([item])
    # cond -> then  and  !cond -> else  => two OR terms joined by one AND
    assert t.count("expr_binary(sp, BIN_OR,") == 2
    assert t.count("expr_binary(sp, BIN_AND,") == 1
    assert t.count("problem_add_constraint(sp,") == 1


def test_if_only_no_else():
    item = ir.ConstraintIfElse(
        cond=_bin(_self("kind"), ir.BinOp.Eq, _c(2)),
        then_body=[ir.ConstraintExpr(expr=_bin(_self("size"), ir.BinOp.Eq, _c(4)))],
        else_body=[])
    t = _text([item])
    assert t.count("expr_binary(sp, BIN_OR,") == 1   # only cond -> then
    assert t.count("expr_binary(sp, BIN_AND,") == 0
    assert t.count("problem_add_constraint(sp,") == 1


def test_unique():
    # unique {a, b, c}  ->  pairwise !=  (3 NEQ terms AND'd), one add
    item = ir.ConstraintUnique(items=[_self("a"), _self("b"), _self("c")])
    t = _text([item])
    assert t.count("expr_binary(sp, BIN_NEQ,") == 3   # ab, ac, bc
    assert t.count("expr_binary(sp, BIN_AND,") == 2   # fold 3 terms
    assert t.count("problem_add_constraint(sp,") == 1


def test_unique_single_item_is_noop():
    assert _emit([ir.ConstraintUnique(items=[_self("a")])]) == []


def test_solve_before_is_noop():
    item = ir.ConstraintSolveBefore(before=[_self("mode")], after=[_self("addr")])
    assert _emit([item]) == []


def test_soft_unsupported():
    with pytest.raises(UnsupportedConstructError):
        _emit([ir.ConstraintSoft(expr=_bin(_self("a"), ir.BinOp.Eq, _c(0)))])


def test_dist_unsupported():
    item = ir.ConstraintDist(target=_self("a"), weights=[ir.DistWeight(rng=_c(0))])
    with pytest.raises(UnsupportedConstructError):
        _emit([item])


def test_foreach_unsupported():
    item = ir.ConstraintForeach(
        array=_self("a"), index_var="i",
        body=[ir.ConstraintExpr(expr=_bin(_self("a"), ir.BinOp.Gt, _c(0)))])
    with pytest.raises(UnsupportedConstructError):
        _emit([item])


def test_nested_implies_in_ifelse():
    # structured (non-expr) body reduces recursively to one boolean ref
    inner = ir.ConstraintImplies(
        antecedent=_bin(_self("a"), ir.BinOp.Gt, _c(0)),
        body=[ir.ConstraintExpr(expr=_bin(_self("b"), ir.BinOp.Lt, _c(8)))])
    item = ir.ConstraintIfElse(
        cond=_bin(_self("mode"), ir.BinOp.Eq, _c(1)),
        then_body=[inner], else_body=[])
    t = _text([item])
    assert t.count("problem_add_constraint(sp,") == 1
    assert "expr_unary(sp, UN_NOT," in t   # both the if-cond and the inner implies

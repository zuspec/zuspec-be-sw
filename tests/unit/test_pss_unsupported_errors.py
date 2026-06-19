"""Phase-6 negative tests: unsupported constructs fail cleanly.

Each unsupported construct must raise ``UnsupportedConstructError`` with an
informative message — never emit a silent stub. Some are caught during lowering
(Layer 0), others by the consolidated Layer-1 pre-flight validator in
``generate_c``.
"""
import tempfile

import pytest

import zuspec.ir.core as ir
from zuspec.ir.core.xf import UnsupportedConstructError

pytest.importorskip("zuspec.fe.pss")
from _pss_harness import lower_pss  # noqa: E402
from zuspec.be.sw.scenario import generate_c  # noqa: E402


# --- caught during lowering (Layer 0) --------------------------------------

def test_abstract_action_rejected():
    pss = """
    component pss_top {
        abstract action base { exec body {} }
        action a { exec body { message(NONE, "a"); } }
    }
    """
    with pytest.raises(UnsupportedConstructError, match="abstract"):
        lower_pss(pss)


def test_unique_constraint_rejected():
    pss = """
    component pss_top {
        action a {
            rand bit[8] x; rand bit[8] y;
            constraint { unique { x, y }; }
            exec body { message(NONE, "a"); }
        }
    }
    """
    with pytest.raises(UnsupportedConstructError):
        lower_pss(pss)


# --- caught by the Layer-1 pre-flight validator ----------------------------

def _emit(module, ctx):
    generate_c(module, ctx, tempfile.mkdtemp())


def test_foreach_loop_rejected():
    module, ctx = lower_pss(
        'component pss_top { action a { exec body { message(NONE,"a"); } } '
        'action t { exec body { message(NONE,"t"); } } }', exports=["t"])
    module.coroutines["t"].body = [
        ir.ScLoop(kind="foreach", iter_var="i", body=[ir.ScInvoke(target="a")])]
    with pytest.raises(UnsupportedConstructError, match="repeat"):
        _emit(module, ctx)


def test_nonconstant_select_weight_rejected():
    module, ctx = lower_pss(
        'component pss_top { action a { exec body { message(NONE,"a"); } } '
        'action t { exec body { message(NONE,"t"); } } }', exports=["t"])
    module.coroutines["t"].body = [ir.ScSelect(branches=[
        ir.ScSelectBranch(
            weight=ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr="w"),
            body=[ir.ScInvoke(target="a")])])]
    with pytest.raises(UnsupportedConstructError, match="constant"):
        _emit(module, ctx)


def test_parallel_nontraversal_branch_rejected():
    module, ctx = lower_pss(
        'component pss_top { action a { exec body { message(NONE,"a"); } } '
        'action t { exec body { message(NONE,"t"); } } }', exports=["t"])
    module.coroutines["t"].body = [ir.ScPar(branches=[
        ir.ScSeq(body=[ir.ScInvoke(target="a")])])]   # ScSeq, not a traversal
    with pytest.raises(UnsupportedConstructError, match="traversal"):
        _emit(module, ctx)


def test_consolidated_report_lists_all():
    """The pre-flight reports multiple problems together."""
    module, ctx = lower_pss(
        'component pss_top { action a { exec body { message(NONE,"a"); } } '
        'action t { exec body { message(NONE,"t"); } } }', exports=["t"])
    module.coroutines["t"].body = [
        ir.ScLoop(kind="foreach", body=[ir.ScInvoke(target="a")]),
        ir.ScPar(branches=[ir.ScSeq(body=[])]),
    ]
    with pytest.raises(UnsupportedConstructError) as ei:
        _emit(module, ctx)
    msg = str(ei.value)
    assert "2 unsupported" in msg

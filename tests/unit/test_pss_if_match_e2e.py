"""Phase-4 e2e: conditional traversal selection (ScIf / ScMatch).

The ``fe-pss`` frontend currently mis-parses activity-level ``if`` (it drops the
branches), so this test exercises the *lowering output + C emitter* directly: it
parses atomic actions via ``fe-pss``, then injects an ``ScIf`` / ``ScMatch`` over
a solved ``sel`` field into the picker coroutine, emits, compiles, and runs —
asserting the branch taken matches the solved value.
"""
import re

import pytest

import zuspec.ir.core as ir
from zuspec.ir.core.expr import BinOp

pytest.importorskip("zuspec.fe.pss")
from zuspec.fe.pss import Parser  # noqa: E402
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator  # noqa: E402
from zuspec.ir.core.xf import PSSToScenarioPass  # noqa: E402
from _pss_harness import require_toolchain  # noqa: E402

PSS = """
component pss_top {
    action a { exec body { message(NONE, "a"); } }
    action b { exec body { message(NONE, "b"); } }
    action picker {
        rand bit[8] sel;
        constraint { sel < 2; }
        exec body { message(NONE, "sel=%d", sel); }
    }
}
"""


def _sel_eq(value: int):
    return ir.ExprBin(
        lhs=ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr="sel"),
        op=BinOp.Eq,
        rhs=ir.ExprConstant(value=value),
    )


def _lower():
    p = Parser()
    p.parses([("p.pss", PSS)])
    ctx = AstToIrTranslator().translate(p.link(), annotations=p.annotations)
    assert not ctx.errors, ctx.errors
    module = PSSToScenarioPass(exports=["picker"]).lower(ctx)
    return module, ctx


def _build_and_run(tmp_path, module, ctx, iters):
    from zuspec.be.sw.scenario import generate_c, build_executable
    import subprocess
    out = tmp_path / "gen"
    srcs = generate_c(module, ctx, out)
    exe = out / "case"
    result, _ = build_executable(srcs, exe, out)
    assert result.success, result.stderr
    run = subprocess.run([str(exe), "777", str(iters)],
                         capture_output=True, text=True, timeout=30)
    return run.stdout, run.returncode


def _check_selection(stdout):
    """Each `sel=N` line is followed by `a` iff N==0, else `b`."""
    lines = [l for l in stdout.splitlines() if l.strip()]
    pairs = list(zip(lines[0::2], lines[1::2]))
    assert pairs, stdout
    seen_a = seen_b = False
    for sel_line, branch in pairs:
        m = re.match(r"sel=(\d+)", sel_line)
        assert m, sel_line
        sel = int(m.group(1))
        assert sel < 2
        expect = "a" if sel == 0 else "b"
        assert branch == expect, f"sel={sel} took {branch}"
        seen_a |= branch == "a"
        seen_b |= branch == "b"
    return seen_a, seen_b


def test_if_selection(tmp_path):
    require_toolchain(needs_solver=True)
    module, ctx = _lower()
    picker = module.coroutines["picker"]
    picker.body.append(ir.ScIf(
        cond=_sel_eq(0),
        then_body=[ir.ScInvoke(target="a")],
        else_body=[ir.ScInvoke(target="b")],
    ))
    stdout, rc = _build_and_run(tmp_path, module, ctx, iters=30)
    assert rc == 0, stdout
    seen_a, seen_b = _check_selection(stdout)
    assert seen_a and seen_b, "both branches should be exercised over 30 runs"


def test_match_selection(tmp_path):
    require_toolchain(needs_solver=True)
    module, ctx = _lower()
    picker = module.coroutines["picker"]
    picker.body.append(ir.ScMatch(
        subject=ir.ExprAttribute(value=ir.TypeExprRefSelf(), attr="sel"),
        cases=[
            ir.ScMatchCase(pattern=ir.ExprConstant(value=0),
                           body=[ir.ScInvoke(target="a")]),
            ir.ScMatchCase(pattern=ir.ExprConstant(value=1),
                           body=[ir.ScInvoke(target="b")]),
        ],
    ))
    stdout, rc = _build_and_run(tmp_path, module, ctx, iters=30)
    assert rc == 0, stdout
    seen_a, seen_b = _check_selection(stdout)
    assert seen_a and seen_b

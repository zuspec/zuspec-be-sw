"""Phase-5 e2e: weighted `select` picks branches per their weights.

`select` is a synchronous weighted choice (no timebase): the emitter renders it
as a root-LCG pick. Over many iterations with weights 3:1, branch `a` should be
hit ~3× as often as `b` (statistical, fixed seed).
"""
import zuspec.ir.core as ir
from _pss_harness import require_toolchain, lower_pss, build_run_module

PSS = """
component pss_top {
    action a { exec body { message(NONE, "a"); } }
    action b { exec body { message(NONE, "b"); } }
    action sel_t { exec body { message(NONE, "ignored"); } }
}
"""


def test_weighted_distribution(tmp_path):
    require_toolchain()
    module, ctx = lower_pss(PSS, exports=["sel_t"])
    module.coroutines["sel_t"].body = [
        ir.ScSelect(branches=[
            ir.ScSelectBranch(weight=ir.ExprConstant(value=3),
                              body=[ir.ScInvoke(target="a")]),
            ir.ScSelectBranch(weight=ir.ExprConstant(value=1),
                              body=[ir.ScInvoke(target="b")]),
        ]),
    ]
    stdout, rc = build_run_module(tmp_path, module, ctx, seed=12345, iters=400)
    assert rc == 0, stdout
    lines = [l for l in stdout.splitlines() if l.strip()]
    na = lines.count("a")
    nb = lines.count("b")
    assert na + nb == 400, stdout
    # Expect ~300:100 (3:1). Allow generous tolerance for the LCG.
    ratio = na / max(1, nb)
    assert 2.0 < ratio < 5.0, f"a={na} b={nb} ratio={ratio:.2f}"

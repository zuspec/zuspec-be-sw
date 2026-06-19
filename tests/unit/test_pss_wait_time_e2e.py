"""Phase-5 e2e: timed `wait` advances the zsp_timebase and the coroutine
resumes in order across suspend points.

A single coroutine prints, waits, prints, waits, prints — rendered as a
switch-on-idx FSM. Asserts the output order (and that the program terminates,
i.e. the timebase advanced past each wait).
"""
import zuspec.ir.core as ir
from _pss_harness import require_toolchain, lower_pss, build_run_module, msg_stmt

PSS = """
component pss_top {
    action w { exec body { message(NONE, "ignored"); } }
}
"""


def test_waits_resume_in_order(tmp_path):
    require_toolchain()
    module, ctx = lower_pss(PSS, exports=["w"])
    # Rebuild w's body as: print t0 → wait 100 → print t1 → wait 50 → print t2.
    module.coroutines["w"].body = [
        ir.ScExecBlock(stmts=[msg_stmt("t0")]),
        ir.ScWait(time=ir.ExprConstant(value=100)),
        ir.ScExecBlock(stmts=[msg_stmt("t1")]),
        ir.ScWait(time=ir.ExprConstant(value=50)),
        ir.ScExecBlock(stmts=[msg_stmt("t2")]),
    ]
    stdout, rc = build_run_module(tmp_path, module, ctx)
    assert rc == 0, stdout
    lines = [l for l in stdout.splitlines() if l.strip()]
    assert lines == ["t0", "t1", "t2"], stdout

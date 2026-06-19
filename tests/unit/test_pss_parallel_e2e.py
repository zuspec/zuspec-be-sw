"""Phase-5 e2e: `parallel { ... }` forks branches on the timebase and joins.

- Both branches run and the parent joins (via fe-pss, no timing).
- With staggered `wait`s, branches interleave by time (proves real
  concurrency on the scheduler, not sequential execution).
"""
import zuspec.ir.core as ir
from _pss_harness import (
    require_toolchain, pss_c_case, lower_pss, build_run_module,
)

PSS = """
component pss_top {
    action a { exec body { message(NONE, "a done"); } }
    action b { exec body { message(NONE, "b done"); } }
    action par_t { activity { parallel { do a; do b; } } }
}
"""


def test_both_branches_run(tmp_path):
    stdout, rc = pss_c_case(tmp_path, PSS, root="pss_top", iters=1)
    assert rc == 0, stdout
    lines = sorted(l for l in stdout.splitlines() if l.strip())
    assert lines == ["a done", "b done"], stdout


def test_interleaving_by_wait(tmp_path):
    require_toolchain()
    module, ctx = lower_pss(PSS, exports=["par_t"])
    # a waits 30ns, b waits 10ns → b completes first.
    module.coroutines["a"].body.insert(0, ir.ScWait(time=ir.ExprConstant(value=30)))
    module.coroutines["b"].body.insert(0, ir.ScWait(time=ir.ExprConstant(value=10)))
    stdout, rc = build_run_module(tmp_path, module, ctx)
    assert rc == 0, stdout
    lines = [l for l in stdout.splitlines() if l.strip()]
    assert lines == ["b done", "a done"], stdout

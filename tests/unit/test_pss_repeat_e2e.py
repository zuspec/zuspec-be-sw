"""Phase-4 e2e: `repeat(N)` count and nested compound traversal."""
import re

from _pss_harness import pss_c_case

PSS = """
component pss_top {
    action a {
        rand bit[8] x;
        constraint { x < 10; }
        exec body { message(NONE, "a x=%d", x); }
    }
    action rep_t {
        activity { repeat (4) { do a; } }
    }
}
"""

NESTED = """
component pss_top {
    action a { exec body { message(NONE, "a"); } }
    action inner { activity { do a; do a; } }
    action outer { activity { repeat (3) { do inner; } } }
}
"""

_A = re.compile(r"a x=(\d+)")


def test_repeat_count(tmp_path):
    stdout, rc = pss_c_case(tmp_path, PSS, seed=5, iters=1, needs_solver=True)
    assert rc == 0, stdout
    vals = _A.findall(stdout)
    assert len(vals) == 4, stdout
    assert all(int(v) < 10 for v in vals)


def test_nested_compound(tmp_path):
    # outer repeats inner 3×, inner does `a` twice → 6 'a' lines.
    stdout, rc = pss_c_case(tmp_path, NESTED, iters=1)
    assert rc == 0, stdout
    lines = [l for l in stdout.splitlines() if l.strip()]
    assert lines == ["a"] * 6, stdout

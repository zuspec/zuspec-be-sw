"""Phase-4 e2e: sequential activity traversal order.

`activity { do a; do b; do c; }` must execute a → b → c, each as an independent
traversal (own solve).
"""
import re

from _pss_harness import pss_c_case

PSS = """
component pss_top {
    action a { exec body { message(NONE, "a"); } }
    action b { exec body { message(NONE, "b"); } }
    action c { exec body { message(NONE, "c"); } }
    action seq_t {
        activity { do a; do b; do c; }
    }
}
"""


def test_sequential_order(tmp_path):
    stdout, rc = pss_c_case(tmp_path, PSS, iters=1)
    assert rc == 0, stdout
    lines = [l for l in stdout.splitlines() if l.strip()]
    assert lines == ["a", "b", "c"], stdout


def test_order_repeats_each_iteration(tmp_path):
    stdout, rc = pss_c_case(tmp_path, PSS, iters=3)
    assert rc == 0
    lines = [l for l in stdout.splitlines() if l.strip()]
    assert lines == ["a", "b", "c"] * 3, stdout

"""Phase-3 e2e: seed reproducibility.

Same root seed ⇒ identical value stream; different seeds ⇒ different streams.
A single root seed drives a root LCG, so a top seed reproduces a whole run.
"""
from _pss_harness import pss_c_case

PSS = """
component pss_top {
    action gen {
        rand bit[32] addr;
        constraint addr_align { (addr & 3) == 0; }
        constraint addr_rng   { addr in [0x1000..0x1FFF]; }
        exec body { message(NONE, "gen: addr=0x%x", addr); }
    }
}
"""


def test_same_seed_reproduces(tmp_path):
    out_a, rc_a = pss_c_case(tmp_path, PSS, seed=42, iters=10, needs_solver=True)
    out_b, rc_b = pss_c_case(tmp_path, PSS, seed=42, iters=10, needs_solver=True)
    assert rc_a == 0 and rc_b == 0
    assert out_a == out_b, "same seed must reproduce the identical stream"


def test_different_seed_differs(tmp_path):
    out_a, _ = pss_c_case(tmp_path, PSS, seed=42, iters=10, needs_solver=True)
    out_c, _ = pss_c_case(tmp_path, PSS, seed=7, iters=10, needs_solver=True)
    assert out_a != out_c, "different seeds should produce different streams"

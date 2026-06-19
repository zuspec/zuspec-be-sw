"""Phase-3 e2e: constrained-random PSS solved at runtime via dv-solve.

Runs N iterations and asserts every generated solution satisfies the action's
constraints (alignment, address range, data range).
"""
import re
from pathlib import Path

import pytest

from _pss_harness import pss_c_case

PSS = """
component pss_top {
    action gen {
        rand bit[32] addr;
        rand bit[32] data;
        constraint addr_align { (addr & 7) == 0; }
        constraint addr_rng   { addr in [0x1000..0x1FFF]; }
        constraint data_rng   { data in [0x10..0x20]; }
        exec body {
            message(NONE, "gen: addr=0x%x data=0x%x", addr, data);
        }
    }
}
"""

_LINE = re.compile(r"gen: addr=0x([0-9a-fA-F]+) data=0x([0-9a-fA-F]+)")


def test_every_solution_satisfies_constraints(tmp_path):
    stdout, rc = pss_c_case(tmp_path, PSS, seed=12345, iters=40,
                            needs_solver=True)
    assert rc == 0, stdout
    matches = _LINE.findall(stdout)
    assert len(matches) == 40, stdout
    for a_hex, d_hex in matches:
        addr = int(a_hex, 16)
        data = int(d_hex, 16)
        assert addr & 7 == 0, f"addr 0x{addr:x} not 8-aligned"
        assert 0x1000 <= addr <= 0x1FFF, f"addr 0x{addr:x} out of range"
        assert 0x10 <= data <= 0x20, f"data 0x{data:x} out of range"


def test_some_variation_across_iterations(tmp_path):
    # A constrained-random run should not collapse to a single value.
    stdout, rc = pss_c_case(tmp_path, PSS, seed=1, iters=30, needs_solver=True)
    assert rc == 0
    addrs = {m[0] for m in _LINE.findall(stdout)}
    assert len(addrs) > 1, "expected more than one distinct addr value"

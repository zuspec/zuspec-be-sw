"""B1 e2e: a compiled C PSS scenario driven from SystemVerilog via the DPI
bridge (Verilator), with the scenario in a runtime libzsp_scenario.so.

Proves the SV factory/export interface drives the C scenario through the generic
zsp_bridge ABI, and that output matches a standalone C run.
"""
import re

from _sv_bridge_harness import run_pss_over_sv

SEQUENCE = """
component pss_top {
    action fetch  { exec body { message(NONE, "fetch");   } }
    action decode { exec body { message(NONE, "decode");  } }
    action exec_a { exec body { message(NONE, "execute"); } }
    action pipeline { activity { do fetch; do decode; do exec_a; } }
}
"""

PARALLEL = """
component pss_top {
    action chan_a { exec body { message(NONE, "channel A"); } }
    action chan_b { exec body { message(NONE, "channel B"); } }
    action both { activity { parallel { do chan_a; do chan_b; } } }
}
"""

CONSTRAINED = """
component pss_top {
    action write_reg {
        rand bit[32] addr;
        constraint a { (addr & 3) == 0; }
        constraint b { addr in [0x1000..0x1FFF]; }
        exec body { message(NONE, "addr=0x%x", addr); }
    }
    action prog { activity { repeat (3) { do write_reg; } } }
}
"""


def test_sequence_over_sv(tmp_path):
    stdout, rc = run_pss_over_sv(tmp_path, SEQUENCE, exports=["pipeline"])
    assert rc == 0, stdout
    body = [l for l in stdout.splitlines() if l in ("fetch", "decode", "execute")]
    assert body == ["fetch", "decode", "execute"], stdout
    assert "[SV] scenario complete" in stdout


def test_parallel_over_sv(tmp_path):
    # The C-side zsp_par_block fork/join runs through the bridge.
    stdout, rc = run_pss_over_sv(tmp_path, PARALLEL, exports=["both"])
    assert rc == 0, stdout
    got = sorted(l for l in stdout.splitlines() if l in ("channel A", "channel B"))
    assert got == ["channel A", "channel B"], stdout


def test_constrained_over_sv(tmp_path):
    # dv-solve linked INTO the scenario .so; solving happens C-side.
    stdout, rc = run_pss_over_sv(tmp_path, CONSTRAINED, exports=["prog"],
                                 needs_solver=True)
    assert rc == 0, stdout
    addrs = [int(m, 16) for m in re.findall(r"addr=0x([0-9a-f]+)", stdout)]
    assert len(addrs) == 3, stdout
    for a in addrs:
        assert a & 3 == 0 and 0x1000 <= a <= 0x1FFF

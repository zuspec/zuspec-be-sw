"""B2 e2e: a C scenario calls a blocking PSS `import target` task in SV.

The non-blocking C coroutine suspends at the import; the SV trampoline forks the
testbench's (time-consuming) import task and re-wakes the coroutine on return.
Covers sequential and concurrent (`parallel`) imports.
"""
import re

from _sv_bridge_harness import run_pss_over_sv

SEQ = """
package dut_api { import target function void do_write(bit[32] addr, bit[32] data); }
component pss_top {
    import dut_api::*;
    action wr {
        rand bit[32] a;
        constraint align { (a & 3) == 0; }
        constraint rng   { a in [0x10..0x40]; }
        exec body { do_write(a, 32'hC0DE); }
    }
    action test { activity { do wr; do wr; } }
}
"""

PAR = SEQ.replace("do wr; do wr;", "parallel { do wr; do wr; }")

TB = """
module tb;
  import zsp_scenario_pkg::*;
  class my_imp extends import_api_base;
    virtual task do_write(input bit [31:0] a0, input bit [31:0] a1);
      #10;
      $display("WRITE addr=0x%0h data=0x%0h @%0t", a0, a1, $time);
    endtask
  endclass
  initial begin
    my_imp        imp = new();
    factory_if    f   = scenario_factory::type_id();
    export_api_if ep  = f.create(imp);
    ep.test();
    $display("[SV] done @%0t", $time);
    $finish;
  end
endmodule
"""

_W = re.compile(r"WRITE addr=0x([0-9a-f]+) data=0x([0-9a-f]+) @(\d+)")


def _check(stdout):
    rows = _W.findall(stdout)
    assert len(rows) == 2, stdout
    for a_hex, d_hex, _t in rows:
        addr = int(a_hex, 16)
        assert addr & 3 == 0 and 0x10 <= addr <= 0x40, f"addr 0x{addr:x}"
        assert int(d_hex, 16) == 0xC0DE
    return [int(r[2]) for r in rows]


def test_sequential_blocking_imports(tmp_path):
    stdout, rc = run_pss_over_sv(tmp_path, SEQ, exports=["test"],
                                 needs_solver=True, custom_tb=TB)
    assert rc == 0, stdout
    times = _check(stdout)
    # Sequential: the two writes complete at staggered times (10, then 20).
    assert times == [10, 20], stdout


def test_parallel_blocking_imports(tmp_path):
    stdout, rc = run_pss_over_sv(tmp_path, PAR, exports=["test"],
                                 needs_solver=True, custom_tb=TB)
    assert rc == 0, stdout
    times = _check(stdout)
    # Concurrent: both forked import tasks complete at the same time (10).
    assert times == [10, 10], stdout

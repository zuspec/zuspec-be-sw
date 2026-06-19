"""B3 e2e: non-blocking `solve` imports — the C side calls a value-returning SV
function SYNCHRONOUSLY (no suspend) via `export "DPI-C"` re-entrancy.

A solve import (`get_addr`) computes an address in SV; its result feeds a
blocking import (`do_write`). Validates the C→SV synchronous return path from a
separate scenario `.so` (`--export-dynamic`).
"""
import re

from _sv_bridge_harness import run_pss_over_sv

PSS = """
package dut_api {
    import solve  function bit[32] get_addr(bit[32] base);
    import target function void   do_write(bit[32] addr, bit[32] data);
}
component pss_top {
    import dut_api::*;
    action wr {
        rand bit[32] base;
        constraint rng { base in [0x10..0x40]; }
        exec body { do_write(get_addr(base), 32'hBEEF); }
    }
    action test { activity { do wr; } }
}
"""

TB = """
module tb;
  import zsp_scenario_pkg::*;
  class my_imp extends import_api_base;
    virtual function bit [31:0] get_addr(input bit [31:0] a0);
      return a0 + 32'h1000;                 // synchronous solve import
    endfunction
    virtual task do_write(input bit [31:0] a0, input bit [31:0] a1);
      #5;
      $display("WRITE addr=0x%0h data=0x%0h", a0, a1);
    endtask
  endclass
  initial begin
    my_imp        imp = new();
    factory_if    f   = scenario_factory::type_id();
    export_api_if ep  = f.create(imp);
    ep.test();
    $display("[SV] done");
    $finish;
  end
endmodule
"""


# Same scenario, but the solve result is bound to a local variable first.
PSS_LOCAL = PSS.replace(
    "exec body { do_write(get_addr(base), 32'hBEEF); }",
    "exec body { bit[32] v = get_addr(base); do_write(v, 32'hBEEF); }")


def _check(stdout):
    m = re.search(r"WRITE addr=0x([0-9a-f]+) data=0x([0-9a-f]+)", stdout)
    assert m, stdout
    addr, data = int(m.group(1), 16), int(m.group(2), 16)
    base = addr - 0x1000          # get_addr added 0x1000 in SV
    assert 0x10 <= base <= 0x40, f"base 0x{base:x} out of constrained range"
    assert data == 0xBEEF


def test_solve_import_feeds_blocking_import(tmp_path):
    stdout, rc = run_pss_over_sv(tmp_path, PSS, exports=["test"],
                                 needs_solver=True, custom_tb=TB)
    assert rc == 0, stdout
    _check(stdout)


def test_solve_import_via_local_var(tmp_path):
    stdout, rc = run_pss_over_sv(tmp_path, PSS_LOCAL, exports=["test"],
                                 needs_solver=True, custom_tb=TB)
    assert rc == 0, stdout
    _check(stdout)

"""B4 e2e: the packaged examples/pss_sv/reg_dut.pss runs through the full
PSS → C `.so` → SystemVerilog DPI bridge on Verilator.

Exercises both import directions concurrently (solve `do_read` + blocking
`do_write` under `parallel`) against a small associative-array DUT model.
"""
import re
from pathlib import Path

from _sv_bridge_harness import run_pss_over_sv

_EXAMPLE = (Path(__file__).resolve().parents[2]
            / "examples" / "pss_sv" / "reg_dut.pss")

TB = """
module tb;
  import zsp_scenario_pkg::*;
  class my_dut extends import_api_base;
    bit [31:0] mem [bit [31:0]];
    virtual function bit [31:0] do_read(input bit [31:0] addr);
      return mem.exists(addr) ? mem[addr] : 0;
    endfunction
    virtual task do_write(input bit [31:0] addr, input bit [31:0] data);
      #10;
      mem[addr] = data;
      $display("WRITE addr=0x%0h data=0x%0h", addr, data);
    endtask
  endclass
  initial begin
    my_dut        imp = new();
    factory_if    f   = scenario_factory::type_id();
    export_api_if ep  = f.create(imp);
    ep.prog();
    $display("[SV] done");
    $finish;
  end
endmodule
"""

_W = re.compile(r"WRITE addr=0x([0-9a-f]+) data=0x([0-9a-f]+)")


def test_reg_dut_example(tmp_path):
    pss = _EXAMPLE.read_text()
    stdout, rc = run_pss_over_sv(tmp_path, pss, exports=["prog"],
                                 needs_solver=True, custom_tb=TB)
    assert rc == 0, stdout
    rows = _W.findall(stdout)
    assert len(rows) == 2, stdout
    for a_hex, d_hex in rows:
        addr, data = int(a_hex, 16), int(d_hex, 16)
        assert 0x1000 <= addr <= 0x1FFF and addr & 3 == 0, f"addr 0x{addr:x}"
        # cur starts 0 → write data == mask, mask in [1, 0xFF]
        assert 1 <= data <= 0xFF, f"data 0x{data:x}"

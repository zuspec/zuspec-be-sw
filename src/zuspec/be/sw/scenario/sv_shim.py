"""Generate the SystemVerilog shim package around the C scenario DPI library.

The shim presents the same interface-class shape as the native PSS→SV flow —
`factory_if` / `import_api_if` / `export_api_if` (+ `export_api_impl`) — but
`export_api_impl` is a trampoline over `libzsp_scenario.so` via a *generic*,
scenario-independent DPI ABI (`zsp_bridge_*`), so the C scenario can be rebuilt
without recompiling the SV.

`import_api_if` is populated from the PSS imports: a blocking ``target`` import
becomes a `task`; the trampoline drains the C scenario's pending import
requests and `fork`s the matching task (so `parallel` imports run concurrently),
then re-wakes the coroutine. (`solve` imports — value functions called
synchronously by the C side via `export "DPI-C"` — arrive in B3.)
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List


_DPI_DECLS = """\
  import "DPI-C" function chandle zsp_bridge_create();
  import "DPI-C" function void    zsp_bridge_destroy(chandle b);
  import "DPI-C" function void    zsp_bridge_spawn(chandle b, int action_id, longint seed);
  import "DPI-C" context function void zsp_bridge_run(chandle b);
  import "DPI-C" function int     zsp_bridge_done(chandle b);
  import "DPI-C" function int     zsp_bridge_next_request(chandle b, output int req_id, output int fn_id);
  import "DPI-C" function longint zsp_bridge_arg(chandle b, int req_id, int idx);
  import "DPI-C" function void    zsp_bridge_complete(chandle b, int req_id, longint ret);
  import "DPI-C" function longint zsp_bridge_solve_arg(chandle b, int idx);
  import "DPI-C" context function void zsp_bridge_capture_scope();"""


def _arg_decl(i: int, width: int, signed: bool) -> str:
    base = "int signed" if signed else "bit"
    if signed:
        return "input bit signed [%d:0] a%d" % (width - 1, i)
    return "input bit [%d:0] a%d" % (width - 1, i)


def generate_sv_shim(action_ids: Dict[str, int], output_dir,
                     imports: List = None,
                     pkg: str = "zsp_scenario_pkg",
                     with_tb: bool = True,
                     default_seed: int = 1) -> Path:
    """Emit ``<pkg>.sv`` (+ optional `tb`). ``imports`` is the module's
    ``ScImportDecl`` list. Returns the generated SV path."""
    all_imports = list(imports or [])
    blocking = [d for d in all_imports if d.blocking]      # target → task
    solve = [d for d in all_imports if not d.blocking]     # solve  → function
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    L: List[str] = ["package %s;" % pkg, _DPI_DECLS, ""]
    for name, aid in action_ids.items():
        L.append("  localparam int ACTION_%s = %d;" % (name, aid))
    for d in all_imports:
        L.append("  localparam int FN_%s = %d;" % (d.name, d.fn_id))
    L.append("")

    def _rty(d):
        w = d.ret_type[0] if d.ret_type else 32
        return "bit [%d:0]" % (w - 1)

    # --- import API: target → task, solve → function ---
    L.append("  interface class import_api_if;")
    for d in blocking:
        args = ", ".join(_arg_decl(i, w, s)
                         for i, (w, s) in enumerate(d.arg_types))
        L.append("    pure virtual task %s(%s);" % (d.name, args))
    for d in solve:
        args = ", ".join(_arg_decl(i, w, s)
                         for i, (w, s) in enumerate(d.arg_types))
        L.append("    pure virtual function %s %s(%s);" % (_rty(d), d.name, args))
    L.append("  endclass")
    L.append("  class import_api_base implements import_api_if;")
    for d in blocking:
        args = ", ".join(_arg_decl(i, w, s)
                         for i, (w, s) in enumerate(d.arg_types))
        L.append("    virtual task %s(%s);" % (d.name, args))
        L.append('      $fatal(1, "import %s not implemented");' % d.name)
        L.append("    endtask")
    for d in solve:
        args = ", ".join(_arg_decl(i, w, s)
                         for i, (w, s) in enumerate(d.arg_types))
        L.append("    virtual function %s %s(%s);" % (_rty(d), d.name, args))
        L.append('      $fatal(1, "import %s not implemented"); return 0;'
                 % d.name)
        L.append("    endfunction")
    L.append("  endclass")
    L.append("")

    # --- synchronous solve-import dispatch (C re-enters SV via export DPI) ---
    L += [
        "  // Active import handle for the synchronous (solve) re-entry path.",
        "  import_api_if g_active_import;",
        "  chandle       g_active_bh;",
        '  export "DPI-C" function zsp_bridge_call_function;',
        "  function longint zsp_bridge_call_function(int fn_id);",
    ]
    if solve:
        L.append("    case (fn_id)")
        for d in solve:
            call_args = ", ".join("zsp_bridge_solve_arg(g_active_bh, %d)" % i
                                  for i in range(len(d.arg_types)))
            L.append("      FN_%s: return g_active_import.%s(%s);"
                     % (d.name, d.name, call_args))
        L.append("      default: return 0;")
        L.append("    endcase")
    else:
        L.append("    return 0;")
    L += ["  endfunction", ""]

    # --- export API ---
    L.append("  interface class export_api_if;")
    for name in action_ids:
        L.append("    pure virtual task %s();" % name)
    L += [
        "  endclass",
        "",
        "  interface class factory_if;",
        "    pure virtual function export_api_if create(import_api_if imp);",
        "  endclass",
        "",
        "  class export_api_impl implements export_api_if;",
        "    chandle       bh;",
        "    import_api_if import_if;",
        "    longint       seed = %d;" % default_seed,
        "    function new(import_api_if imp);",
        "      import_if = imp;",
        "      bh = zsp_bridge_create();",
        "    endfunction",
    ]

    # dispatch_task: route a blocking request fn_id to the testbench import task
    L.append("    task automatic dispatch_task(int fn_id, int rid);")
    if blocking:
        L.append("      case (fn_id)")
        for d in blocking:
            call_args = ", ".join("zsp_bridge_arg(bh, rid, %d)" % i
                                  for i in range(len(d.arg_types)))
            L.append("        FN_%s: import_if.%s(%s);"
                     % (d.name, d.name, call_args))
        L.append("        default: ;")
        L.append("      endcase")
    L.append("    endtask")

    # the trampoline event loop
    L += [
        "    task automatic run_action(int action_id);",
        "      int rid, fid;",
        "      int outstanding = 0;",
        "      event progress;",
        "      g_active_import = import_if;",   # for synchronous solve re-entry
        "      g_active_bh = bh;",
        "      zsp_bridge_capture_scope();",     # so the export call has a scope
        "      zsp_bridge_spawn(bh, action_id, seed);",
        "      forever begin",
        "        zsp_bridge_run(bh);",
        "        while (zsp_bridge_next_request(bh, rid, fid)) begin",
        "          automatic int l_rid = rid;",
        "          automatic int l_fid = fid;",
        "          outstanding++;",
        "          fork begin",
        "            dispatch_task(l_fid, l_rid);",
        "            zsp_bridge_complete(bh, l_rid, 0);",   # void target → ret 0
        "            outstanding--;",
        "            ->progress;",
        "          end join_none",
        "        end",
        "        if (zsp_bridge_done(bh) && outstanding == 0) break;",
        "        @progress;",
        "      end",
        "    endtask",
    ]
    for name in action_ids:
        L += ["    virtual task %s();" % name,
              "      run_action(ACTION_%s);" % name,
              "    endtask"]
    L += [
        "  endclass",
        "",
        "  class scenario_factory implements factory_if;",
        "    static scenario_factory self;",
        "    static function scenario_factory type_id();",
        "      if (self == null) self = new();",
        "      return self;",
        "    endfunction",
        "    virtual function export_api_if create(import_api_if imp);",
        "      export_api_impl r = new(imp);",
        "      return r;",
        "    endfunction",
        "  endclass",
        "endpackage",
        "",
    ]

    if with_tb:
        L += [
            "module tb;",
            "  import %s::*;" % pkg,
            "  initial begin",
            "    import_api_base imp = new();",
            "    factory_if    f  = scenario_factory::type_id();",
            "    export_api_if ep = f.create(imp);",
        ]
        for name in action_ids:
            L.append("    ep.%s();" % name)
        L += ['    $display("[SV] scenario complete");', "    $finish;",
              "  end", "endmodule", ""]

    path = out / ("%s.sv" % pkg)
    path.write_text("\n".join(L))
    return path

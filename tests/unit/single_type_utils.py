
import io
import os
import pytest
import shutil
import subprocess

import zsp_arl_dm.core as arl_dm

class FindRefs(arl_dm.VisitorBase):

    def __init__(self):
        super().__init__()
    
    def visitDataTypeStruct(self, t):
        print("Found struct: %s" % t.name())

    def visitDataTypeArlStruct(self, t):
        print("Found arl struct: %s" % t.name())
        super().visitDataTypeArlStruct(t)

def run_single_type_test(rundir, pss_src, typename, c_src, exp, prefix="RES: ", debug=False):
    unit_tests_dir = os.path.dirname(__file__)
    zsp_be_sw_dir = os.path.abspath(os.path.join(unit_tests_dir, "..", ".."))
    zsp_be_sw_incdir = os.path.join(zsp_be_sw_dir, "src/include")
    zsp_be_sw_libdir = os.path.join(zsp_be_sw_dir, "build/lib")

    with open(os.path.join(rundir, "test.c"), "w") as fp:
        fp.write(c_src)

    with open(os.path.join(rundir, "test.pss"), "w") as fp:
        fp.write(pss_src)

    import debug_mgr.core as dmgr
    dmgr_f = dmgr.Factory.inst()
    dmgr_i = dmgr_f.getDebugMgr()
    if debug:
        dmgr_i.enable(True)

    import vsc_dm.core as vsc_dm
    import zsp_arl_dm.core as arl_dm
    arl_ctxt = arl_dm.Factory().inst().mkContext(
        vsc_dm.Factory().inst().mkContext()
    )
    import zsp_be_sw.core as be_sw
    be_f = be_sw.Factory.inst()
    be_ctxt = be_f.mkContext(arl_ctxt)

    import zsp_parser.core as parser
    parser_f = parser.Factory.inst()

    marker_c = parser_f.mkMarkerCollector()
    ast_builder = parser_f.mkAstBuilder(marker_c)
    ast_linker = parser_f.mkAstLinker()

    import zsp_fe_parser.core as fe_parser
    zsp_fe_f = fe_parser.Factory.inst()

    ast_l = []

    core_lib = parser_f.getAstFactory().mkGlobalScope(len(ast_l))
    parser_f.loadStandardLibrary(ast_builder, core_lib)
    ast_l.append(core_lib)

    ast_root = parser_f.getAstFactory().mkGlobalScope(len(ast_l))

    with open(os.path.join(rundir, "test.pss"), "r") as fp:
        ast_builder.build(ast_root, fp)
    ast_l.append(ast_root)

    status = 0

    for m in marker_c.markers():
        print("Marker")

    if status == 0:
        linked_root = ast_linker.link(marker_c, ast_l)

    if status == 0:
        import zsp_fe_parser.core as fe_parser
        zsp_fe_f = fe_parser.Factory.inst()
        ast2arl_builder = zsp_fe_f.mkAst2ArlBuilder()
        ast2arl_ctxt = zsp_fe_f.mkAst2ArlContext(
            arl_ctxt,
            linked_root,
            marker_c)
    
        ast2arl_builder.build(linked_root, ast2arl_ctxt)

    if status == 0:
        pss_top = arl_ctxt.findDataTypeStruct(typename)

        assert pss_top is not None

        print("--> finding")
        finder = FindRefs()
        finder.visit(pss_top)
        print("<-- finding")

#        out_c = open(os.path.join(rundir, "%s.c" % typename), "w")
#        out_h = open(os.path.join(rundir, "%s.h" % typename), "w")

        print("pss_top")
        be_f.generateTypes(be_ctxt, pss_top, rundir)

#        out_c.close()
#        out_h.close()

        c_srcs = []
        for f in os.listdir(rundir):
            if f.endswith('.c'):
                c_srcs.append(os.path.join(rundir, f))

        gcc = shutil.which("gcc")
        print("gcc: %s" % gcc)

        for i,c_src in enumerate(c_srcs):
            cmd = [
                gcc, "-g", "-c", c_src,
                "-I%s" % os.path.join(rundir),
                "-I%s" % zsp_be_sw_incdir]
            
            print("Command: %s" % " ".join(cmd))
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=rundir)
#                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
#                fp = open(os.path.join(rundir, "gcc_%d.out" % i), "w")
#                proc = subprocess.run(cmd, stdout=fp, stderr=subprocess.STDOUT, cwd=rundir)
                proc = subprocess.run(cmd)
                fp.close()
                if proc.returncode != 0:
                    fp = open(os.path.join(rundir, "gcc_%d.out" % i), "r")
                    log = fp.read()
                    fp.close()
                    raise Exception("Failed to compile %s\n%s" % (c_src, log))

                print("Compiled %s" % c_src)
            except subprocess.CalledProcessError as e:
                print("Failed to compile %s" % c_src)
                print("Error: %s" % e.stdout.decode())
                raise e

        link_cmd = [
            gcc, "-g", "-o", os.path.join(rundir, "test.exe"),
        ]
        for i,c_src in enumerate(c_srcs):
            c_obj = os.path.basename(c_src).replace(".c", ".o")
            link_cmd.append(os.path.join(rundir, c_obj))

        link_cmd.extend([
            "-L%s" % zsp_be_sw_libdir,
            "-Wl,-rpath,%s" % zsp_be_sw_libdir,
            "-lzsp-be-sw-rt",
        ])

        try:
            print("Link command: %s" % " ".join(link_cmd))
            result = subprocess.check_output(link_cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print("Failed to link %s" % c_src)
            print("Error: %s" % e.stdout.decode())
            raise e
        print("Linked %s" % c_src)

        try:
            result = subprocess.check_output([
                os.path.join(rundir, "test.exe")],
                stderr=subprocess.STDOUT,
                cwd=rundir)
        except subprocess.CalledProcessError as e:
            print("Failed to run %s" % c_src)
            print("Error: %s" % e.stdout.decode())
            raise e

        print("result: %s" % result.decode())

        exp_lines = exp.strip().splitlines()
        act_lines = result.decode().strip().splitlines()

        if prefix is not None:
            i=0
            while i < len(act_lines):
                if not act_lines[i].startswith(prefix):
                    act_lines.pop(i)
                else:
                    i += 1

        if len(exp_lines) != len(act_lines):
            print("Expected:\n%s" % "\n".join(exp_lines))
            print("Actual:\n%s" % "\n".join(act_lines))
            raise Exception("Output does not match expected output")
        else:
            match = True
            for i in range(len(exp_lines)):
                if exp_lines[i].strip() == act_lines[i].strip():
                    print("Pass: %s" % exp_lines[i].strip())
                else:
                    print("Fail: %s (%s)" % (act_lines[i].strip(), exp_lines[i].strip()))
                    match = False

            if not match:
                print("Expected:\n%s" % "\n".join(exp_lines))
                print("Actual:\n%s" % "\n".join(act_lines))
                raise Exception("Output does not match expected output")

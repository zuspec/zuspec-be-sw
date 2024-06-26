import io
import os
import shutil
import subprocess
import unittest

class TestBase(unittest.TestCase):

    def setUp(self) -> None:
        import os
        import sys
        unit_dir = os.path.dirname(os.path.abspath(__file__))
        test_dir = os.path.dirname(unit_dir)
        self.data_dir = os.path.join(unit_dir, "data")
        self.proj_dir = os.path.abspath(os.path.join(unit_dir, "../.."))

        self.run_dir = os.path.join(test_dir, "rundir")
        self.test_dir = os.path.join(self.run_dir, "test")

        if os.path.isdir(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        os.makedirs(self.test_dir)

        sys.path.insert(0, os.path.join(self.proj_dir, "python"))

        import zsp_be_sw.core as be_sw
        import zsp_arl_dm.core as arl_dm
        self.be_sw_f = be_sw.Factory.inst()

        self.arl_dm_f = arl_dm.Factory.inst()

        return super().setUp()
    
    def tearDown(self) -> None:
        return super().tearDown()
    
    def genBuildRun(self,
                    content,
                    comp_t,
                    action_t,
                    extra_hdr=None,
                    extra_src=None):
        arl_ctxt, comp_t, action_t = self.buildModelGetRoots(
            content,
            comp_t,
            action_t)

        c_out = open(os.path.join(self.test_dir, "model.c"), "w")
        h_out = open(os.path.join(self.test_dir, "model.h"), "w")
        h_prv_out = open(os.path.join(self.test_dir, "model_prv.h"), "w")

        h_out.write("#include \"zsp_rt.h\"\n")

        c_out.write("#include <stdint.h>\n")
        c_out.write("#include <stdlib.h>\n")
        c_out.write("#include <stdio.h>\n")
        c_out.write("#include <string.h>\n")
        c_out.write("#include \"zsp_rt.h\"\n")
        c_out.write("#include \"model.h\"\n")
        c_out.write("#include \"model_prv.h\"\n")

        if extra_hdr is not None:
            for hdr in extra_hdr:
                c_out.write("#include \"%s\"\n" % (
                    os.path.basename(hdr)))

        self.be_sw_f.generateExecModel(
            arl_ctxt,
            comp_t,
            action_t,
            c_out,
            h_out,
            h_prv_out
        )

        c_out.close()
        h_out.close()
        h_prv_out.close()

        actor_name = comp_t.name() + "_" + action_t.name()
        actor_name = actor_name.replace(':', '_')

        with open(os.path.join(self.test_dir, "driver.c"), "w") as fp:
            fp.write("#include \"model.h\"\n")
            fp.write("\n")
            fp.write("int main() {\n")
            fp.write("    zsp_rt_actor_mgr_t mgr;\n")
            fp.write("    zsp_rt_actor_t *actor;\n")
            fp.write("    zsp_rt_actor_mgr_init(&mgr);\n")
            fp.write("    actor = %s_new(&mgr);\n" % (actor_name))
            fp.write("\n")
            fp.write("    while (zsp_rt_run_one_task(actor)) { ; }\n")
            fp.write("}\n")

        cmd = ['gcc', '-g', '-o', os.path.join(self.test_dir, 'test.exe')]

        cmd.append(os.path.join(self.proj_dir, 'runtime/zsp_rt_posix.c'))
        cmd.append(os.path.join(self.test_dir, 'model.c'))
        cmd.append(os.path.join(self.test_dir, 'driver.c'))
        cmd.append('-I' + self.test_dir)
        cmd.append('-I' + os.path.join(self.proj_dir, 'runtime'))
        if extra_hdr is not None:
            for hdr in extra_hdr:
                cmd.append('-I' + os.path.dirname(hdr))

        if extra_src is not None:
            for src in extra_src:
                cmd.append('-I' + os.path.dirname(src))
                cmd.append(src)

        ret = subprocess.run(cmd)

        if ret.returncode != 0:
            raise Exception("Compile failed")
        
        cmd = [os.path.join(self.test_dir, "test.exe")]
        ret = subprocess.run(cmd)

        if ret.returncode != 0:
            raise Exception("Run failed")
    
    def buildModelGetRoots(
            self,
            content,
            comp_t,
            action_t):
        import zsp_fe_parser.core as zsp_fe
        import zsp_arl_dm.core as zsp_arl
        import zsp_parser.core as zspp

        factory = zsp_fe.Factory.inst()
        factory.getDebugMgr().enable(True)

        arl_f = zsp_arl.Factory.inst()
        arl_ctxt = arl_f.mkContext()

        zsp_f = zspp.Factory.inst()
        marker_c = zsp_f.mkMarkerCollector()
        ast_builder = zsp_f.mkAstBuilder(marker_c)
        ast_linker = zsp_f.mkAstLinker()
        zsp_fe_f = zsp_fe.Factory.inst()

        ast_root = zsp_f.getAstFactory().mkGlobalScope(0)
        ast_builder.build(ast_root, io.StringIO(content))

        for m in marker_c.markers():
            print("Parse Marker: %s" % m.msg())
        self.assertFalse(marker_c.hasSeverity(zspp.MarkerSeverityE.Error))

        linked_root = ast_linker.link(marker_c, [ast_root])
        for m in marker_c.markers():
            print("Linker Marker: %s" % m.msg())
        self.assertFalse(marker_c.hasSeverity(zspp.MarkerSeverityE.Error))

        ast2arl_builder = zsp_fe_f.mkAst2ArlBuilder()
        ast2arl_ctxt = zsp_fe_f.mkAst2ArlContext(
            arl_ctxt,
            linked_root,
            marker_c)
        
        ast2arl_builder.build(linked_root, ast2arl_ctxt)

        pss_top = arl_ctxt.findDataTypeStruct(comp_t)
        self.assertIsNotNone(pss_top)
        print("pss_top=%s" % str(pss_top))

        pss_top_Entry = arl_ctxt.findDataTypeStruct(action_t)
        self.assertIsNotNone(pss_top_Entry)

        return (arl_ctxt, pss_top, pss_top_Entry)
    

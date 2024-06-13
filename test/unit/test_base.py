import io
import unittest

class TestBase(unittest.TestCase):

    def setUp(self) -> None:
        import os
        import sys
        unit_dir = os.path.dirname(os.path.abspath(__file__))
        proj_dir = os.path.abspath(os.path.join(unit_dir, "../.."))

        sys.path.insert(0, os.path.join(proj_dir, "python"))

        import zsp_be_sw.core as be_sw
        import zsp_arl_dm.core as arl_dm
        self.be_sw_f = be_sw.Factory.inst()

        self.arl_dm_f = arl_dm.Factory.inst()

        return super().setUp()
    
    def tearDown(self) -> None:
        return super().tearDown()
    
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

        self.assertFalse(marker_c.hasSeverity(zspp.MarkerSeverityE.Error))

        linked_root = ast_linker.link(marker_c, [ast_root])
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
    

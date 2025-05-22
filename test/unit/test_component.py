import pytest
import io


def test_smoke(tmpdir):
    pss_top = """
component pss_top {
    int a;
}
"""

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

    ast_builder.build(ast_root, io.StringIO(pss_top))
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
        pss_top = arl_ctxt.findDataTypeStruct("pss_top")

        out_c = io.StringIO()
        out_h = io.StringIO()

        print("pss_top")
        be_f.generateType(be_ctxt, pss_top, out_c, out_h)

        print("C: %s" % out_c.getvalue())
        pass
        

#    import zsp_fe_parser.core as fe_parser
#    fe_parser_ctxt = fe_parser.Factory().inst().mkContext(be_ctxt)


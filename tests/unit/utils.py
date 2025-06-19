import io
import logging
import os

def parse_load_src(pss_src):
    import zsp_arl_dm.core as arl_dm

    import debug_mgr.core as dmgr
    dmgr_f = dmgr.Factory.inst()
    dmgr_i = dmgr_f.getDebugMgr()

    if logging.DEBUG >= logging.root.level:
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

    ast_builder.build(ast_root, io.StringIO(pss_src))
    ast_l.append(ast_root)

    status = 0

    for m in marker_c.markers():
        print("Marker: %s" % m.msg())

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
    return arl_ctxt

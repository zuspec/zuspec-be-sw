
import io
import logging
import os
import pytest
import shutil
import subprocess

import zsp_arl_dm.core as arl_dm

def generate_model(rundir, pss_src, actions=None, debug=False):
    unit_tests_dir = os.path.dirname(__file__)
    zsp_be_sw_dir = os.path.abspath(os.path.join(unit_tests_dir, "..", ".."))
    zsp_be_sw_incdir = os.path.join(zsp_be_sw_dir, "src/include")
    zsp_be_sw_libdir = os.path.join(zsp_be_sw_dir, "build/lib")

    with open(os.path.join(rundir, "test.pss"), "w") as fp:
        fp.write(pss_src)

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
        pss_top = arl_ctxt.findDataTypeStruct("pss_top")

        assert pss_top is not None

#        out_c = open(os.path.join(rundir, "%s.c" % typename), "w")
#        out_h = open(os.path.join(rundir, "%s.h" % typename), "w")

        actor_l = []

        if actions is not None:
            if not isinstance(actions, list):
                actions = [actions]
            for aname in actions:
                atype = arl_ctxt.findDataTypeStruct(aname)
                actor_l.append(atype)

        print("pss_top")
        be_f.generateModel(
            be_ctxt, 
            pss_top, 
            actor_l, 
            os.path.join(rundir, "model"))
        
        srcs = []
        for f in os.listdir(os.path.join(rundir, "model")):
            if f.endswith(".c"):
                srcs.append(os.path.join(rundir, "model", f))
        
        cmd = ["gcc", "-o", os.path.join(rundir, "model", "libmodel.so"),
               "-shared", "-fPIC", "-g",
               ]
        cmd.append("-I%s" % os.path.join(rundir, "model"))
        cmd.append("-I%s" % zsp_be_sw_incdir)
        cmd.extend(srcs)
        cmd.append("-L%s" % zsp_be_sw_libdir)
        cmd.append("-lzsp-be-sw-rt")
        cmd.append("-Wl,-rpath,%s" % zsp_be_sw_libdir)

        result = subprocess.run(cmd)

        assert result.returncode == 0


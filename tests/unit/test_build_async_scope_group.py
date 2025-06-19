import pytest
from .utils import parse_load_src

def test_yield_1(tmpdir):
    pss_top = """
    target function void test() {
        yield;
        yield;
    }
"""
    from zsp_be_sw.core import Factory as BeSwFactory

    be_sw_f = BeSwFactory.inst()

    arl_dm_ctxt = parse_load_src(pss_top)
    test_f = arl_dm_ctxt.findDataTypeFunction("test")

    print("Parsed source:", test_f.getBody())

    ctxt = be_sw_f.mkContext(arl_dm_ctxt)

    scope = be_sw_f.buildAsyncScopeGroup(ctxt, test_f.getBody())
    print("Scope:", scope)
    pass

def test_activity_1(tmpdir):
    pss_top = """
    component pss_top {
        action A { }
        action B { }
        action Entry {
            activity {
                do A;
                do B;
            }
        }
    }
"""
    from zsp_be_sw.core import Factory as BeSwFactory

    be_sw_f = BeSwFactory.inst()

    arl_dm_ctxt = parse_load_src(pss_top)
    entry_a = arl_dm_ctxt.findDataTypeStruct("pss_top::Entry")

    print("Parsed source:", entry_a)

    ctxt = be_sw_f.mkContext(arl_dm_ctxt)

    scope = be_sw_f.buildAsyncScopeGroup(ctxt, entry_a)
    print("Scope:", scope)
    pass
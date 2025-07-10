import asyncio
import os
import pytest
from .model_utils import generate_model
from zsp_be_sw.model import Model

def test_call_1(tmpdir):
    pss_top = """
import target function void doit();
//import solve function bool condition2();
//import solve function void report_branch(int branch_num);

component pss_top {
    action Entry {
        exec body {
            doit();
            doit();
            doit();
            doit();
            doit();
            doit();
            doit();
            /*
             */
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    async def doit():
        print("doit", flush=True)
        pass

    # TODO: fix name mangling
    actor = model.mk_actor("pss_top::Entry")
    asyncio.run(actor.run())

def test_repeat_1(tmpdir):
    pss_top = """
import target function void doit();

component pss_top {
    action Entry {
        exec body {
            repeat (i : 6) {
                int x;
                doit();
                // 
            }
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    async def doit():
        print("doit", flush=True)
        pass

    actor = model.mk_actor("pss_top::Entry")
    asyncio.run(actor.run())
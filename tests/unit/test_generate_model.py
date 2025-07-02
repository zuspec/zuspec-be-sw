import asyncio
import os
import pytest
from .model_utils import generate_model
from zsp_be_sw.model import Model

def test_smoke(tmpdir):
    pss_top = """
import solve function void doit(int i);
//import target function void doit2(int i);

component pss_top {
    int a = 5;


    action Entry {
        exec post_solve {
            print("Hello World!\\n");
            doit(20);
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)

    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    for t in model.actor_type_m.keys():
        print("Actor Type: %s" % t)

    def doit(val):
        print("doit: %d" % val, flush=True)
        pass

    actor = model.mk_actor()

    asyncio.run(actor.run())

    pass

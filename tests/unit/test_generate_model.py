import pytest
from .model_utils import generate_model

def test_smoke(tmpdir):
    pss_top = """
import solve function void doit(int i);
import target function void doit2(int i);

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

    pass

import pytest
from .model_utils import generate_model

def test_smoke(tmpdir):
    pss_top = """
component pss_top {
    int a = 5;

    exec init_down {
        print("Hello World!\\n");
    }

    action Entry {

    }
}
"""
    generate_model(tmpdir, pss_top, debug=True)

    pass

import pytest
import io
import os

from .single_type_utils import run_single_type_test


def test_smoke(tmpdir):
    pss_top = """
component pss_top {
    int a;

    exec init_down {
    }
}
"""

    test_c = """
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_actor.h"
#include "pss_top.h"

int main() {
    zsp_actor(pss_top) pss_top;

    pss_top__init((zsp_actor_t *)&pss_top, &pss_top.comp);

}
"""

    exp = """
"""

    run_single_type_test(
        os.path.join(tmpdir), 
        pss_src=pss_top, 
        typename="pss_top", 
        c_src=test_c,
        exp=exp,
        debug=True
    )
        


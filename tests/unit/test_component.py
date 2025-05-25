import pytest
import io
import os

from .single_type_utils import run_single_type_test


def test_smoke(tmpdir):
    pss_top = """
component pss_top {
    int a = 5;

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

    pss_top__init((zsp_actor_t *)&pss_top, &pss_top.comp, "pss_top", 0);
    fprintf(stdout, "RES: comp.a=%d\\n", pss_top.comp.a);

}
"""

    exp = """
RES: comp.a=5
"""

    run_single_type_test(
        os.path.join(tmpdir), 
        pss_src=pss_top, 
        typename="pss_top", 
        c_src=test_c,
        exp=exp,
        debug=True
    )

def test_init_down(tmpdir):
    pss_top = """
import std_pkg::*;

component pss_top {
    int a = 5;

    exec init_down {
        a = 10;
    }
}
"""

    test_c = """
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_actor.h"
#include "pss_top.h"

int main() {
    zsp_actor(pss_top) pss_top;

    zsp_actor_init(
        (zsp_actor_t *)&pss_top, 
        0, 
        (zsp_component_type_t *)pss_top__type(), 
        (zsp_action_type_t *)0);
    fprintf(stdout, "RES: comp.a=%d\\n", pss_top.comp.a);

}
"""

    exp = """
RES: comp.a=10
"""

    run_single_type_test(
        os.path.join(tmpdir), 
        pss_src=pss_top, 
        typename="pss_top", 
        c_src=test_c,
        exp=exp,
        debug=True
    )        


import io
import os
import pytest
import shutil
import subprocess

from .single_type_utils import run_single_type_test


def test_smoke(tmpdir):
    pss_top = """
struct my_data_type_s {
    int a = 2;
}
"""

    test_c = """
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_actor.h"
#include "my_data_type_s.h"

int main() {
    my_data_type_s_t data;
    zsp_actor_t *actor = 0;

    my_data_type_s__init(actor, &data);
    fprintf(stdout, "RES: my_s.a = %d\\n", data.a);
    return 0;
}
"""

    exp = """
RES: my_s.a = 2
"""

    run_single_type_test(
        os.path.join(tmpdir), 
        pss_top, 
        "my_data_type_s", 
        test_c,
        exp,
        debug=False)

def test_inheritance(tmpdir):
    pss_top = """
struct my_base_type_s {
    int a = 1;
}

struct my_data_type_s : my_base_type_s {
    int b = 2;
}
"""

    test_c = """
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_actor.h"
#include "my_data_type_s.h"

int main() {
    my_data_type_s_t data;
    zsp_actor_t *actor = 0;

    my_data_type_s__init(actor, &data);
    fprintf(stdout, "RES: my_s.a=%d my_s.b=%d\\n", data.a, data.b);
    return 0;
}
"""

    exp = """
RES: my_s.a=1 my_s.b=2
"""

    run_single_type_test(
        os.path.join(tmpdir), 
        pss_top, 
        "my_data_type_s", 
        test_c,
        exp,
        debug=False)


def test_struct_field(tmpdir):
    pss_top = """

struct s1 {
    int x = 10;
}

struct s2 {
    int x = 20;
}

struct my_data_type_s {
    int a = 2;
    s1 b;
    s2 c;
}
"""

    test_c = """
#include <stdio.h>
#include "zsp/be/sw/rt/zsp_actor.h"
#include "my_data_type_s.h"

int main() {
    my_data_type_s_t data;
    zsp_actor_t *actor = 0;

    my_data_type_s__init(actor, &data);
    fprintf(stdout, "RES: my_s.a=%d my_s.b.x=%d\\n", data.a, data.b.x);
    return 0;
}
"""

    exp = """
RES: my_s.a=2 my_s.b.x=10
"""

    run_single_type_test(
        os.path.join(tmpdir), 
        pss_top, 
        "my_data_type_s", 
        test_c,
        exp,
        debug=False)


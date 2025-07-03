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

    count = 0
    def doit(val):
        nonlocal count
        print("doit: %d" % val, flush=True)
        count += 1
        pass

    actor = model.mk_actor()

    asyncio.run(actor.run())

    assert count == 1

    pass

def test_smoke_2(tmpdir):
    pss_top = """
import target function void doit(int i);

component pss_top {
    int a = 5;

    action Entry {
        exec body {
            doit(20);
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)

    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    for t in model.actor_type_m.keys():
        print("Actor Type: %s" % t)

    count = 0
    async def doit(val):
        nonlocal count
        print("doit: %d" % val, flush=True)
        count += 1
        pass

    actor = model.mk_actor()

    asyncio.run(actor.run())

    assert count == 1

    pass

def test_import_sum(tmpdir):
    pss_top = """
import solve function int get_value1();
import solve function int get_value2(); 
import solve function void report_sum(int sum);

component pss_top {
    action Entry {
        exec post_solve {
            int val1;
            int val2;
            val1 = get_value1();
            val2 = get_value2();
            report_sum(val1 + val2);
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)

    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    for t in model.actor_type_m.keys():
        print("Actor Type: %s" % t)

    # Test cases with different input values
    test_values = [
        (5, 7),      # Small positive numbers
        (100, 200),  # Larger positive numbers
        (0, 42),     # Zero and positive
        (-10, 20),   # Negative and positive
        (-5, -3)     # Both negative
    ]

    for val1, val2 in test_values:
        # Setup test values and result tracking
        current_val1 = val1
        current_val2 = val2
        sum_reported = None

        def get_value1():
            return current_val1

        def get_value2():
            return current_val2

        def report_sum(val):
            nonlocal sum_reported
            sum_reported = val
            print(f"Sum reported for {current_val1} + {current_val2} = {val}", flush=True)

        actor = model.mk_actor()
        asyncio.run(actor.run())

        # Verify the sum calculation
        expected_sum = current_val1 + current_val2
        assert sum_reported == expected_sum, f"Sum mismatch for {current_val1} + {current_val2}: expected {expected_sum}, got {sum_reported}"

    pass

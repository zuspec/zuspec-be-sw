import asyncio
import os
import pytest
from .model_utils import generate_model
from zsp_be_sw.model import Model

def test_simple_if_else(tmpdir):
    pss_top = """
import solve function bool get_condition();
import solve function void report_branch(int branch_num);

component pss_top {
    action Entry {
        exec post_solve {
            if (get_condition()) {
                report_branch(1);
            } else {
                report_branch(2);
            }
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    # Test both true and false conditions
    test_cases = [(True, 1), (False, 2)]
    
    for condition, expected_branch in test_cases:
        current_condition = condition
        reported_branch = None

        def get_condition():
            return current_condition

        def report_branch(branch):
            nonlocal reported_branch
            reported_branch = branch

        actor = model.mk_actor()
        asyncio.run(actor.run())

        assert reported_branch == expected_branch, f"Expected branch {expected_branch} for condition {condition}"

def test_if_integer_condition(tmpdir):
    pss_top = """
import solve function int get_value();
import solve function void report_branch(int branch_num);

component pss_top {
    action Entry {
        exec post_solve {
            if (get_value() > 5) {
                report_branch(1);
            }
            if (get_value() <= 5) {
                report_branch(2);
            }
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    # Test values above and below threshold
    test_cases = [(10, 1), (3, 2)]
    
    for value, expected_branch in test_cases:
        current_value = value
        reported_branch = None

        def get_value():
            return current_value

        def report_branch(branch):
            nonlocal reported_branch
            reported_branch = branch

        actor = model.mk_actor()
        asyncio.run(actor.run())

        assert reported_branch == expected_branch, f"Expected branch {expected_branch} for value {value}"

def test_nested_if_else(tmpdir):
    pss_top = """
import solve function bool outer_condition();
import solve function bool inner_condition();
import solve function void report_branch(int branch_num);

component pss_top {
    action Entry {
        exec post_solve {
            if (outer_condition()) {
                if (inner_condition()) {
                    report_branch(1);
                } else {
                    report_branch(2);
                }
            } else {
                report_branch(3);
            }
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    # Test all possible combinations
    test_cases = [
        (True, True, 1),   # outer true, inner true
        (True, False, 2),  # outer true, inner false
        (False, True, 3),  # outer false (inner doesn't matter)
        (False, False, 3)  # outer false (inner doesn't matter)
    ]
    
    for outer, inner, expected_branch in test_cases:
        current_outer = outer
        current_inner = inner
        reported_branch = None

        def outer_condition():
            return current_outer

        def inner_condition():
            return current_inner

        def report_branch(branch):
            nonlocal reported_branch
            reported_branch = branch

        actor = model.mk_actor()
        asyncio.run(actor.run())

        assert reported_branch == expected_branch, f"Expected branch {expected_branch} for outer={outer}, inner={inner}"

def test_if_else_if_chain(tmpdir):
    pss_top = """
import solve function bool condition1();
import solve function bool condition2();
import solve function void report_branch(int branch_num);

component pss_top {
    action Entry {
        exec post_solve {
            if (condition1()) {
                report_branch(1);
            } else if (condition2()) {
                report_branch(2);
            } else {
                report_branch(3);
            }
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    # Test all possible combinations
    test_cases = [
        (True, True, 1),    # First condition true (second doesn't matter)
        (True, False, 1),   # First condition true (second doesn't matter)
        (False, True, 2),   # First false, second true
        (False, False, 3)   # Both conditions false
    ]
    
    for cond1, cond2, expected_branch in test_cases:
        current_cond1 = cond1
        current_cond2 = cond2
        reported_branch = None

        def condition1():
            return current_cond1

        def condition2():
            return current_cond2

        def report_branch(branch):
            nonlocal reported_branch
            reported_branch = branch

        actor = model.mk_actor()
        asyncio.run(actor.run())

        assert reported_branch == expected_branch, f"Expected branch {expected_branch} for cond1={cond1}, cond2={cond2}"

@pytest.mark.skip
def test_if_else_local_vars(tmpdir):
    pss_top = """
import solve function int get_value();
import solve function void report_result(int val);

component pss_top {
    action Entry {
        exec post_solve {
            int x;
            if (get_value() > 5) {
                int positive = get_value() * 2;
                report_result(positive);
            } else {
                int negative = get_value() * -1;
                report_result(negative);
            }
            x = 42;
            report_result(x);
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    # Test both branches and verify final x value
    test_cases = [(10, 20, 42), (3, -3, 42)]  # (input, expected first result, expected x)
    
    for value, expected_first, expected_x in test_cases:
        current_value = value
        results = []

        def get_value():
            print("get_value: %d" % current_value)
            return current_value

        def report_result(val):
            print("report_result: %d" % val)
            results.append(val)

        actor = model.mk_actor()
        asyncio.run(actor.run())

        assert len(results) == 2, "Expected two results reported"
        assert results[0] == expected_first, f"Expected first result {expected_first} for value {value}, got {results[0]}"
        assert results[1] == expected_x, f"Expected x value {expected_x}, got {results[1]}"

def test_repeat_1(tmpdir):
    pss_top = """
import solve function void doit(int i);

component pss_top {
    action Entry {
        exec post_solve {
            repeat (i : 6) {
                int x;
                doit(i);
            }
        }
    }
}
"""
    generate_model(tmpdir, pss_top, "pss_top::Entry", debug=True)
    model = Model.load(os.path.join(tmpdir, "model", "libmodel.so"))

    def doit(i):
        print("doit: %d" % i)

    actor = model.mk_actor("pss_top::Entry")
    asyncio.run(actor.run())



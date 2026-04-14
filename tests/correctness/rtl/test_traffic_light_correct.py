"""Correctness tests for TrafficLight FSM compiled via zuspec-be-sw."""
import ctypes
import pytest


@pytest.fixture(scope="module")
def tl_so(compile_and_load, TrafficLight):
    lib, State = compile_and_load(TrafficLight)
    lib.TrafficLight_init.argtypes = [ctypes.POINTER(State)]
    lib.TrafficLight_init.restype = None
    lib.TrafficLight_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.TrafficLight_clock_edge.restype = None
    lib.TrafficLight_eval_comb.argtypes = [ctypes.POINTER(State)]
    lib.TrafficLight_eval_comb.restype = None
    return lib, State


def _fresh(lib, State):
    st = State()
    lib.TrafficLight_init(ctypes.byref(st))
    return st


def _tick(lib, st):
    lib.TrafficLight_clock_edge(ctypes.byref(st))
    lib.TrafficLight_eval_comb(ctypes.byref(st))


def test_reset_holds_red(tl_so):
    """reset=1 keeps state RED (red=1, amber=0, green=0)."""
    lib, State = tl_so
    st = _fresh(lib, State)
    st.reset = 1
    st.hold = 0
    for _ in range(5):
        _tick(lib, st)
    assert st.red == 1
    assert st.amber == 0
    assert st.green == 0


def test_state_sequence_no_hold(tl_so):
    """With hold=0, states cycle RED→RED_AMBER→GREEN→AMBER→RED in 4 ticks."""
    lib, State = tl_so
    st = _fresh(lib, State)
    # Start: apply reset for 1 cycle
    st.reset = 1
    st.hold = 0
    _tick(lib, st)
    assert st.red == 1 and st.amber == 0 and st.green == 0  # RED

    st.reset = 0
    _tick(lib, st)
    assert st.red == 1 and st.amber == 1 and st.green == 0  # RED_AMBER

    _tick(lib, st)
    assert st.red == 0 and st.amber == 0 and st.green == 1  # GREEN

    _tick(lib, st)
    assert st.red == 0 and st.amber == 1 and st.green == 0  # AMBER

    _tick(lib, st)
    assert st.red == 1 and st.amber == 0 and st.green == 0  # back to RED


def test_hold_extends_state(tl_so):
    """hold=1 means 2 cycles per state (1 base + 1 extra)."""
    lib, State = tl_so
    st = _fresh(lib, State)
    st.reset = 1
    st.hold = 1
    _tick(lib, st)
    assert st.red == 1 and st.green == 0  # still RED

    st.reset = 0
    _tick(lib, st)
    # timer goes 0→1 but 1 == hold so should NOT advance state yet
    assert st.red == 1 and st.amber == 0 and st.green == 0  # still RED

    _tick(lib, st)
    # Now timer was reset, state should advance to RED_AMBER
    assert st.red == 1 and st.amber == 1 and st.green == 0  # RED_AMBER

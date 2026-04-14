"""Correctness tests for PriorityEncoder compiled via zuspec-be-sw."""
import ctypes
import pytest


@pytest.fixture(scope="module")
def pe_so(compile_and_load, PriorityEncoder):
    lib, State = compile_and_load(PriorityEncoder)
    lib.PriorityEncoder_init.argtypes = [ctypes.POINTER(State)]
    lib.PriorityEncoder_init.restype = None
    lib.PriorityEncoder_eval_comb.argtypes = [ctypes.POINTER(State)]
    lib.PriorityEncoder_eval_comb.restype = None
    return lib, State


def _eval(lib, State, req):
    st = State()
    lib.PriorityEncoder_init(ctypes.byref(st))
    st.req = req
    lib.PriorityEncoder_eval_comb(ctypes.byref(st))
    return st.valid, st.idx


def test_no_request(pe_so):
    lib, State = pe_so
    valid, idx = _eval(lib, State, 0)
    assert valid == 0
    assert idx == 0


def test_bit0_request(pe_so):
    lib, State = pe_so
    valid, idx = _eval(lib, State, 0b0001)
    assert valid == 1
    assert idx == 0


def test_bit1_request(pe_so):
    lib, State = pe_so
    valid, idx = _eval(lib, State, 0b0010)
    assert valid == 1
    assert idx == 1


def test_bit2_request(pe_so):
    lib, State = pe_so
    valid, idx = _eval(lib, State, 0b0100)
    assert valid == 1
    assert idx == 2


def test_bit3_request(pe_so):
    lib, State = pe_so
    valid, idx = _eval(lib, State, 0b1000)
    assert valid == 1
    assert idx == 3


def test_priority_lowest_wins(pe_so):
    """When multiple bits set, lowest index wins."""
    lib, State = pe_so
    valid, idx = _eval(lib, State, 0b1010)  # bits 1 and 3
    assert valid == 1
    assert idx == 1

"""Correctness tests for Counter compiled via zuspec-be-sw."""
import ctypes
import pytest


@pytest.fixture(scope="module")
def counter_so(compile_and_load, Counter):
    lib, State = compile_and_load(Counter)
    lib.Counter_init.argtypes = [ctypes.POINTER(State)]
    lib.Counter_init.restype = None
    lib.Counter_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.Counter_clock_edge.restype = None
    lib.Counter_advance.argtypes = [ctypes.POINTER(State)]
    lib.Counter_advance.restype = None
    lib.Counter_apply_reset.argtypes = [ctypes.POINTER(State)]
    lib.Counter_apply_reset.restype = None
    return lib, State


def _fresh(lib, State):
    st = State()
    lib.Counter_init(ctypes.byref(st))
    return st


def _apply_reset(lib, st):
    lib.Counter_apply_reset(ctypes.byref(st))


def test_reset_holds_at_zero(counter_so):
    """apply_reset() → count=0; enable=0 keeps count at 0 for 10 edges."""
    lib, State = counter_so
    st = _fresh(lib, State)
    _apply_reset(lib, st)
    st.enable = 0
    for _ in range(10):
        lib.Counter_clock_edge(ctypes.byref(st))
    assert st.count == 0


def test_count_increments(counter_so):
    """After apply_reset(), enable=1, N clock_edge() → count == N."""
    lib, State = counter_so
    st = _fresh(lib, State)
    _apply_reset(lib, st)
    st.enable = 1
    N = 20
    for _ in range(N):
        lib.Counter_clock_edge(ctypes.byref(st))
    assert st.count == N


def test_enable_gate(counter_so):
    """enable=0 → count frozen."""
    lib, State = counter_so
    st = _fresh(lib, State)
    _apply_reset(lib, st)
    # Count to 5
    st.enable = 1
    for _ in range(5):
        lib.Counter_clock_edge(ctypes.byref(st))
    assert st.count == 5
    # Disable — count must not change
    st.enable = 0
    for _ in range(10):
        lib.Counter_clock_edge(ctypes.byref(st))
    assert st.count == 5


def test_reset_mid_run(counter_so):
    """Count 5, apply_reset(), count should immediately go to 0."""
    lib, State = counter_so
    st = _fresh(lib, State)
    _apply_reset(lib, st)
    st.enable = 1
    for _ in range(5):
        lib.Counter_clock_edge(ctypes.byref(st))
    assert st.count == 5
    # Assert reset — domain-based: reset values applied immediately
    _apply_reset(lib, st)
    assert st.count == 0


def test_count_wraps_32bit(counter_so):
    """Counter wraps around at 2^32."""
    lib, State = counter_so
    st = _fresh(lib, State)
    # Set count close to max using direct struct access
    st.count = 0xFFFF_FFFE
    st.count_nxt = 0xFFFF_FFFE
    st.enable = 1
    lib.Counter_clock_edge(ctypes.byref(st))
    assert st.count == 0xFFFF_FFFF
    lib.Counter_clock_edge(ctypes.byref(st))
    assert st.count == 0  # wrapped

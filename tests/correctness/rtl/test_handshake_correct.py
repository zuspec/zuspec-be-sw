"""Correctness tests for DataSource and DataSink compiled via zuspec-be-sw."""
import ctypes
import pytest


@pytest.fixture(scope="module")
def source_so(compile_and_load, DataSource):
    lib, State = compile_and_load(DataSource)
    lib.DataSource_init.argtypes = [ctypes.POINTER(State)]
    lib.DataSource_init.restype = None
    lib.DataSource_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.DataSource_clock_edge.restype = None
    return lib, State


@pytest.fixture(scope="module")
def sink_so(compile_and_load, DataSink):
    lib, State = compile_and_load(DataSink)
    lib.DataSink_init.argtypes = [ctypes.POINTER(State)]
    lib.DataSink_init.restype = None
    lib.DataSink_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.DataSink_clock_edge.restype = None
    return lib, State


# ---- DataSource tests ----

def test_source_reset_clears_valid(source_so):
    lib, State = source_so
    st = State()
    lib.DataSource_init(ctypes.byref(st))
    st.reset = 1
    lib.DataSource_clock_edge(ctypes.byref(st))
    assert st.io.valid == 0
    assert st.io.data == 0


def test_source_asserts_valid_after_reset(source_so):
    lib, State = source_so
    st = State()
    lib.DataSource_init(ctypes.byref(st))
    st.reset = 0
    st.io.ready = 0
    lib.DataSource_clock_edge(ctypes.byref(st))
    assert st.io.valid == 1


def test_source_increments_data_on_ready(source_so):
    lib, State = source_so
    st = State()
    lib.DataSource_init(ctypes.byref(st))
    st.reset = 0
    st.io.ready = 1
    for i in range(5):
        lib.DataSource_clock_edge(ctypes.byref(st))
    assert st.io.data == 5


def test_source_data_frozen_without_ready(source_so):
    lib, State = source_so
    st = State()
    lib.DataSource_init(ctypes.byref(st))
    # Advance to data=3
    st.reset = 0
    st.io.ready = 1
    for _ in range(3):
        lib.DataSource_clock_edge(ctypes.byref(st))
    assert st.io.data == 3
    # Freeze
    st.io.ready = 0
    for _ in range(5):
        lib.DataSource_clock_edge(ctypes.byref(st))
    assert st.io.data == 3


# ---- DataSink tests ----

def test_sink_reset_clears_received(sink_so):
    lib, State = sink_so
    st = State()
    lib.DataSink_init(ctypes.byref(st))
    st.reset = 1
    lib.DataSink_clock_edge(ctypes.byref(st))
    assert st.received == 0
    assert st.io.ready == 0


def test_sink_counts_transfers(sink_so):
    lib, State = sink_so
    st = State()
    lib.DataSink_init(ctypes.byref(st))
    st.reset = 0
    st.io.valid = 1
    for _ in range(7):
        lib.DataSink_clock_edge(ctypes.byref(st))
    assert st.received == 7


def test_sink_no_count_without_valid(sink_so):
    lib, State = sink_so
    st = State()
    lib.DataSink_init(ctypes.byref(st))
    st.reset = 0
    st.io.valid = 0
    for _ in range(10):
        lib.DataSink_clock_edge(ctypes.byref(st))
    assert st.received == 0

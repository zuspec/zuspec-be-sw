"""Correctness tests for MultAccPipeline compiled via zuspec-be-sw."""
import ctypes
import sys
from pathlib import Path

import pytest

# Ensure pipeline module is importable for ACCUM_MAX
_EX = Path(__file__).parents[5] / "examples" / "05_pipeline"
if str(_EX) not in sys.path:
    sys.path.insert(0, str(_EX))

from pipeline import ACCUM_MAX


@pytest.fixture(scope="session")
def MultAccPipeline():
    from pipeline import MultAccPipeline as C
    return C


@pytest.fixture(scope="module")
def pipeline_so(compile_and_load, MultAccPipeline):
    lib, State = compile_and_load(MultAccPipeline)
    lib.MultAccPipeline_init.argtypes = [ctypes.POINTER(State)]
    lib.MultAccPipeline_init.restype = None
    lib.MultAccPipeline_clock_edge.argtypes = [ctypes.POINTER(State)]
    lib.MultAccPipeline_clock_edge.restype = None
    return lib, State


def _fresh(lib, State):
    st = State()
    lib.MultAccPipeline_init(ctypes.byref(st))
    return st


def test_accumulates_product(pipeline_so):
    """sum grows by a*b each cycle."""
    lib, State = pipeline_so
    st = _fresh(lib, State)
    st.a = 3
    st.b = 4
    for i in range(1, 6):
        lib.MultAccPipeline_clock_edge(ctypes.byref(st))
        assert st.sum == 12 * i, f"cycle {i}: expected {12*i}, got {st.sum}"


def test_saturates_at_accum_max(pipeline_so):
    """Saturating accumulator caps at ACCUM_MAX."""
    lib, State = pipeline_so
    st = _fresh(lib, State)
    # 0x8000 * 0x8000 = 2^30; after 1100 cycles: 1100*2^30 > 2^40-1
    st.a = 0x8000
    st.b = 0x8000
    for _ in range(1100):
        lib.MultAccPipeline_clock_edge(ctypes.byref(st))
    assert st.sum == ACCUM_MAX


def test_zero_inputs_no_accumulation(pipeline_so):
    """a=0 or b=0 means product=0, sum stays unchanged."""
    lib, State = pipeline_so
    st = _fresh(lib, State)
    st.a = 5
    st.b = 0
    for _ in range(10):
        lib.MultAccPipeline_clock_edge(ctypes.byref(st))
    assert st.sum == 0

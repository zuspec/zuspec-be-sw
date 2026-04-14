"""
Behavioral correctness tests for wait_time.

Tests use TimedCounter (count += 1 every delay_ns nanoseconds)
on a 10 ns clock domain (period_ps=10000).
"""
import ctypes
import sys
from pathlib import Path
import pytest

_EXAMPLES = Path(__file__).parents[5] / "examples"


@pytest.fixture(scope="session")
def TimedCounter():
    ex_dir = str(_EXAMPLES / "06_delay_counter")
    if ex_dir not in sys.path:
        sys.path.insert(0, ex_dir)
    import importlib
    mod = importlib.import_module("timed_counter")
    return mod.TimedCounter


class TestWaitTime:
    def test_100ns_on_10ns_clock_is_10_cycles(
        self, compile_so_behav, TimedCounter
    ):
        """wait_time(100, NS) on 10 ns clock → fires every 10 cycles."""
        lib, State = compile_so_behav(TimedCounter, domain_period_ps=10_000)
        lib.TimedCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.TimedCounter_sim_run.restype = None
        s = State()
        lib.TimedCounter_init(ctypes.byref(s))
        s.delay_ns = 100
        lib.TimedCounter_sim_run(ctypes.byref(s), 10)
        assert s.count == 1
        lib.TimedCounter_sim_run(ctypes.byref(s), 10)
        assert s.count == 2

    def test_95ns_on_10ns_clock_rounds_up_to_10_cycles(
        self, compile_so_behav, TimedCounter
    ):
        """wait_time(95, NS) → ceil(95ns/10ns)=10 cycles (rounds up)."""
        lib, State = compile_so_behav(TimedCounter, domain_period_ps=10_000)
        lib.TimedCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.TimedCounter_sim_run.restype = None
        s = State()
        lib.TimedCounter_init(ctypes.byref(s))
        s.delay_ns = 95  # rounds up to 100ns = 10 cycles
        lib.TimedCounter_sim_run(ctypes.byref(s), 10)
        assert s.count == 1

    def test_50ns_on_10ns_clock_is_5_cycles(
        self, compile_so_behav, TimedCounter
    ):
        """wait_time(50, NS) → 5 cycles on 10 ns clock."""
        lib, State = compile_so_behav(TimedCounter, domain_period_ps=10_000)
        lib.TimedCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.TimedCounter_sim_run.restype = None
        s = State()
        lib.TimedCounter_init(ctypes.byref(s))
        s.delay_ns = 50
        lib.TimedCounter_sim_run(ctypes.byref(s), 10)
        assert s.count == 2  # at cycles 5 and 10

    def test_runtime_delay_ns_register(
        self, compile_so_behav, TimedCounter
    ):
        """Runtime delay_ns register: delay=5ns → ceil(5/10)=1 cycle."""
        lib, State = compile_so_behav(TimedCounter, domain_period_ps=10_000)
        lib.TimedCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.TimedCounter_sim_run.restype = None
        s = State()
        lib.TimedCounter_init(ctypes.byref(s))
        s.delay_ns = 5   # 5ns → ceil(5000/10000) = 1 cycle
        lib.TimedCounter_sim_run(ctypes.byref(s), 5)
        assert s.count == 5  # fires every cycle (5ns rounds up to 10ns=1 cycle)

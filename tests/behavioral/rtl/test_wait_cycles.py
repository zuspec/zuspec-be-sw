"""
Behavioral correctness tests for wait_cycles.

Tests use the DelayCounter example (count += 1 every ``delay`` cycles).
After N cycles with delay D: count = N // D (integer division).
"""
import ctypes
import pytest


class TestWaitCycles:
    def test_wait_5_cycles_advances_correctly(self, compile_so_behav, DelayCounter):
        """After 5 cycles with delay=5: count=1."""
        lib, State = compile_so_behav(DelayCounter)
        s = State()
        lib.DelayCounter_init(ctypes.byref(s))
        s.delay = 5
        lib.DelayCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.DelayCounter_sim_run.restype = None
        lib.DelayCounter_sim_run(ctypes.byref(s), 5)
        assert s.count == 1

    def test_wait_1_cycle_increments_every_cycle(self, compile_so_behav, DelayCounter):
        """delay=1: after N cycles count==N."""
        lib, State = compile_so_behav(DelayCounter)
        s = State()
        lib.DelayCounter_init(ctypes.byref(s))
        s.delay = 1
        lib.DelayCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.DelayCounter_sim_run.restype = None
        for n in [1, 5, 10]:
            s2 = State()
            lib.DelayCounter_init(ctypes.byref(s2))
            s2.delay = 1
            lib.DelayCounter_sim_run(ctypes.byref(s2), n)
            assert s2.count == n, f"delay=1, n={n}: expected {n}, got {s2.count}"

    def test_wait_3_cycles_divides_correctly(self, compile_so_behav, DelayCounter):
        """delay=3: count = floor(n/3)."""
        lib, State = compile_so_behav(DelayCounter)
        lib.DelayCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.DelayCounter_sim_run.restype = None
        for n, expected in [(3, 1), (6, 2), (9, 3), (10, 3), (12, 4)]:
            s = State()
            lib.DelayCounter_init(ctypes.byref(s))
            s.delay = 3
            lib.DelayCounter_sim_run(ctypes.byref(s), n)
            assert s.count == expected, f"delay=3, n={n}: expected {expected}, got {s.count}"

    def test_multi_call_accumulates(self, compile_so_behav, DelayCounter):
        """Multiple sim_run calls accumulate correctly."""
        lib, State = compile_so_behav(DelayCounter)
        s = State()
        lib.DelayCounter_init(ctypes.byref(s))
        s.delay = 3
        lib.DelayCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.DelayCounter_sim_run.restype = None
        lib.DelayCounter_sim_run(ctypes.byref(s), 9)   # count=3
        assert s.count == 3
        lib.DelayCounter_sim_run(ctypes.byref(s), 3)   # count=4
        assert s.count == 4
        lib.DelayCounter_sim_run(ctypes.byref(s), 6)   # count=6
        assert s.count == 6

    def test_wait_0_cycles_yields_without_advancing(self, compile_so_behav, DelayCounter):
        """delay=0 → wait_cycles(0) → yield at same tick; count each cycle."""
        # Special case: wait_cycles(0) means yield — coroutine fires every cycle.
        lib, State = compile_so_behav(DelayCounter)
        lib.DelayCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
        lib.DelayCounter_sim_run.restype = None
        s = State()
        lib.DelayCounter_init(ctypes.byref(s))
        s.delay = 0
        lib.DelayCounter_sim_run(ctypes.byref(s), 3)
        # wait_cycles(0) → is_yield (co_wake == tick each cycle) → fires every cycle
        assert s.count == 3

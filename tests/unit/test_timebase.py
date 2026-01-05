import pytest
import asyncio
import io
import sys
import zuspec.dataclasses as zdc
from zuspec.dataclasses.rt.timebase import Timebase


def test_smoke(tmpdir):
    """Test basic component with time() and wait() calls."""
    
    @zdc.dataclass
    class MyC(zdc.Component):

        async def doit(self):
            print("Time: %s" % self.time())
            await self.wait(zdc.Time.ns(1))
            print("Time: %s" % self.time())

    # Capture stdout
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    
    try:
        # Create component - timebase is automatically created
        comp = MyC()
        
        # Run the async method using the component's wait mechanism
        async def run_test():
            await comp.doit()
        
        asyncio.run(run_test())
        
    finally:
        sys.stdout = old_stdout
    
    output = captured.getvalue()
    print(f"Output: {output}")
    
    # Check that time 0 and 1ns are displayed
    assert "Time: 0.0ns" in output or "Time: 0ns" in output
    assert "Time: 1.0ns" in output or "Time: 1ns" in output


def test_timebase_creation():
    """Test that timebase is created with component."""
    @zdc.dataclass
    class TestComp(zdc.Component):
        pass
    
    comp = TestComp()
    
    # Component should have an impl with a timebase
    assert comp._impl is not None
    tb = comp._impl.timebase()
    assert tb is not None
    assert isinstance(tb, Timebase)


def test_time_initial_zero():
    """Test that initial time is zero."""
    @zdc.dataclass
    class TestComp(zdc.Component):
        pass
    
    comp = TestComp()
    t = comp.time()
    
    # Initial time should be 0
    assert t.amt == 0


def test_wait_advances_time():
    """Test that wait() advances simulation time."""
    @zdc.dataclass
    class TestComp(zdc.Component):
        
        async def do_wait(self):
            t_before = self.time()
            await self.wait(zdc.Time.ns(50))
            t_after = self.time()
            return (t_before, t_after)
    
    comp = TestComp()
    
    async def run_test():
        return await comp.do_wait()
    
    t_before, t_after = asyncio.run(run_test())
    
    assert t_before.amt == 0
    # After waiting 50ns, time should be 50ns
    assert t_after.as_ns() == 50.0


def test_multiple_waits():
    """Test multiple sequential waits."""
    results = []
    
    @zdc.dataclass
    class TestComp(zdc.Component):
        
        async def multi_wait(self):
            results.append(self.time().as_ns())
            await self.wait(zdc.Time.ns(10))
            results.append(self.time().as_ns())
            await self.wait(zdc.Time.ns(20))
            results.append(self.time().as_ns())
            await self.wait(zdc.Time.ns(30))
            results.append(self.time().as_ns())
    
    comp = TestComp()
    
    async def run_test():
        await comp.multi_wait()
    
    asyncio.run(run_test())
    
    # Times should be: 0, 10, 30, 60 (cumulative)
    assert results == [0.0, 10.0, 30.0, 60.0]


def test_time_units():
    """Test different time units."""
    @zdc.dataclass
    class TestComp(zdc.Component):
        
        async def test_units(self):
            times = []
            times.append(self.time().as_ns())
            
            await self.wait(zdc.Time.us(1))  # 1 microsecond = 1000 ns
            times.append(self.time().as_ns())
            
            await self.wait(zdc.Time.ns(500))
            times.append(self.time().as_ns())
            
            return times
    
    comp = TestComp()
    
    async def run_test():
        return await comp.test_units()
    
    times = asyncio.run(run_test())
    
    assert times[0] == 0.0
    assert times[1] == 1000.0  # 1us = 1000ns
    assert times[2] == 1500.0  # 1000 + 500


def test_delta_wait():
    """Test wait with delta time (0 delay)."""
    call_count = 0
    
    @zdc.dataclass
    class TestComp(zdc.Component):
        
        async def delta_test(self):
            nonlocal call_count
            t1 = self.time().as_ns()
            call_count += 1
            await self.wait(zdc.Time.delta())  # Delta time
            t2 = self.time().as_ns()
            call_count += 1
            return t1, t2
    
    comp = TestComp()
    
    async def run_test():
        return await comp.delta_test()
    
    t1, t2 = asyncio.run(run_test())
    
    # Delta wait should not advance time
    assert t1 == t2 == 0.0
    assert call_count == 2


def test_child_component_inherits_timebase():
    """Test that child components inherit parent's timebase."""
    
    @zdc.dataclass
    class Child(zdc.Component):
        async def get_time(self):
            return self.time()
    
    @zdc.dataclass
    class Parent(zdc.Component):
        child: Child = zdc.field(default_factory=Child)
        
        async def run_child(self):
            t1 = self.time()
            await self.wait(zdc.Time.ns(100))
            t2 = await self.child.get_time()
            return t1, t2
    
    parent = Parent()
    
    async def run_test():
        return await parent.run_child()
    
    t1, t2 = asyncio.run(run_test())
    
    # Parent starts at 0
    assert t1.as_ns() == 0.0
    # Child should see the advanced time (100ns)
    assert t2.as_ns() == 100.0


def test_time_string_representation():
    """Test Time string representation."""
    t_ns = zdc.Time.ns(42)
    assert "42" in str(t_ns)
    assert "ns" in str(t_ns)
    
    t_us = zdc.Time.us(5)
    assert "5" in str(t_us)
    assert "us" in str(t_us)
    
    t_ms = zdc.Time.ms(100)
    assert "100" in str(t_ms)
    assert "ms" in str(t_ms)

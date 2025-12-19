"""
Test fixtures for method call testing.

These components must be in a separate file for DataModelFactory source introspection.
"""

import zuspec.dataclasses as zdc


@zdc.dataclass
class ComponentWithMethod(zdc.Component):
    """Component with methods to test method calling."""
    counter: zdc.bit32 = zdc.output()
    
    def reset(self):
        """Reset the counter to zero."""
        self.counter = 0
    
    def add_values(self, a: int, b: int) -> int:
        """Add two values and return the result."""
        result = a + b
        self.counter = result
        return result
    
    def get_counter(self) -> int:
        """Get the current counter value."""
        return self.counter
    
    def set_counter(self, value: int):
        """Set the counter value."""
        self.counter = value


@zdc.dataclass
class ComponentWithProcess(zdc.Component):
    """Component with a process for testing event loop integration."""
    counter: zdc.bit32 = zdc.output()
    enable: zdc.bit1 = zdc.input()
    
    @zdc.process
    async def run_process(self):
        """Simple process that increments counter."""
        while True:
            if self.enable:
                self.counter = self.counter + 1
            await self.wait()  # Wait one cycle


@zdc.dataclass
class ComponentWithWait(zdc.Component):
    """Component with wait() calls in process."""
    done: zdc.bit1 = zdc.output()
    
    @zdc.process
    async def delayed_process(self):
        """Process with explicit delays."""
        await self.wait(1000)  # Wait 1000 time units
        self.done = 1


# TODO: Add port/export components once we understand the syntax
# @zdc.dataclass
# class Provider(zdc.Component):
#     """Component that exports an interface."""
#     pass
# 
# @zdc.dataclass  
# class Consumer(zdc.Component):
#     """Component that uses a port."""
#     pass


@zdc.dataclass
class ComponentWithArray(zdc.Component):
    """Component with array-typed signals."""
    # TODO: Determine array syntax in zuspec
    # array_signal: List[zdc.bit8] = zdc.output()
    pass


@zdc.dataclass
class ComponentWithStruct(zdc.Component):
    """Component with struct-typed signals."""
    # TODO: Determine struct syntax in zuspec
    pass


@zdc.dataclass
class ParentComponent(zdc.Component):
    """Parent component with nested child."""
    output_val: zdc.bit32 = zdc.output()
    # child_comp: ChildComponent = zdc.field(default_factory=ChildComponent)


@zdc.dataclass
class ChildComponent(zdc.Component):
    """Child component for nesting test."""
    value: zdc.bit32 = zdc.output()

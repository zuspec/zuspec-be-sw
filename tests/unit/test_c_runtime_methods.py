"""
Tests for C runtime method call support.

Test-driven development for Phase 2.1: Method Wrappers
"""

import pytest
import tempfile
from pathlib import Path

# Check if backend is available
try:
    from zuspec.dataclasses.rt.c_rt import CObjFactory
    import zuspec.dataclasses as zdc
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False


# Test fixtures must be in separate file for source introspection
# For now, define a simple one here to see what fails


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
class TestMethodCalls:
    """Test calling methods on C components."""
    
    def test_method_exists_in_proxy(self):
        """Test that methods are visible as attributes on proxy."""
        from fixtures.method_components import ComponentWithMethod
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = CObjFactory(cache_dir=Path(tmpdir))
            comp = factory.mkComponent(ComponentWithMethod)
            assert hasattr(comp, 'add_values')
            assert callable(comp.add_values)
    
    def test_call_simple_method_no_args(self):
        """Test calling a method with no arguments."""
        from fixtures.method_components import ComponentWithMethod
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = CObjFactory(cache_dir=Path(tmpdir))
            comp = factory.mkComponent(ComponentWithMethod)
            comp.set_counter(100)
            comp.reset()
            assert comp.counter == 0
    
    def test_call_method_with_args(self):
        """Test calling a method with arguments."""
        from fixtures.method_components import ComponentWithMethod
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = CObjFactory(cache_dir=Path(tmpdir))
            comp = factory.mkComponent(ComponentWithMethod)
            result = comp.add_values(10, 32)
            assert result == 42
    
    def test_call_method_with_return_value(self):
        """Test calling a method that returns a value."""
        from fixtures.method_components import ComponentWithMethod
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = CObjFactory(cache_dir=Path(tmpdir))
            comp = factory.mkComponent(ComponentWithMethod)
            comp.set_counter(100)
            result = comp.get_counter()
            assert result == 100


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
class TestProcessSupport:
    """Test process support (requires event loop integration)."""
    
    def test_component_with_process_compiles(self):
        """Test that a component with @process can be compiled."""
        from fixtures.method_components import ComponentWithProcess
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = CObjFactory(cache_dir=Path(tmpdir))
            comp = factory.mkComponent(ComponentWithProcess)
            assert comp is not None
    
    def test_process_execution(self):
        """Test that process startup code is generated."""
        from fixtures.method_components import ComponentWithProcess
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = CObjFactory(cache_dir=Path(tmpdir))
            comp = factory.mkComponent(ComponentWithProcess)
            
            # Verify start_processes method exists and is callable
            assert hasattr(comp, 'start_processes')
            assert callable(comp.start_processes)
            
            # Call start_processes - should not crash
            comp.start_processes()
            
            # NOTE: The generated process task is currently a placeholder.
            # The thread creation and scheduling depends on the C timebase
            # implementation details. The key accomplishment is that:
            # 1. Process task wrappers are generated
            # 2. start_processes function is generated
            # 3. The code compiles and links correctly
            #
            # Full process execution with actual process bodies requires
            # the async-to-sync converter to generate complete process
            # implementations, which is future work.
    
    def test_process_with_wait(self):
        """Test that timebase time advancement works."""
        from fixtures.method_components import ComponentWithWait
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = CObjFactory(cache_dir=Path(tmpdir))
            comp = factory.mkComponent(ComponentWithWait)
            
            # Verify timebase is at time 0
            assert comp.timebase_current_time() == 0
            
            # Try to advance (should work even with no events)
            comp.timebase_advance()
            
            # Time should still be 0 (no events to advance to)
            assert comp.timebase_current_time() == 0
            
            # Verify done signal is initially 0
            assert comp.done == 0
            
            # NOTE: Actually running the process with wait() would require:
            # 1. C generator to emit process startup code
            # 2. Process to be started with start_processes()
            # 3. Timebase to advance through the wait period
            # This is deferred to future work when process generation is complete.


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")  
class TestPortExportBindings:
    """Test port/export binding support."""
    
    def test_port_attribute_exists(self):
        """Test that ports are accessible as attributes."""
        pytest.skip("TODO: Need to research port/export syntax first")
    
    def test_export_attribute_exists(self):
        """Test that exports are accessible as attributes."""
        pytest.skip("TODO: Need to research port/export syntax first")
    
    def test_bind_port_to_export(self):
        """Test binding a port to an export."""
        pytest.skip("TODO: Need to research port/export syntax first")
    
    def test_call_through_port(self):
        """Test calling a method through a bound port."""
        pytest.skip("TODO: Need to research port/export syntax first")


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
class TestComplexTypes:
    """Test support for complex types."""
    
    def test_array_signal(self):
        """Test array-typed signals."""
        pytest.skip("TODO: Need to research array syntax first")
    
    def test_struct_signal(self):
        """Test struct-typed signals."""
        pytest.skip("TODO: Need to research struct syntax first")
    
    def test_nested_component_access_denied(self):
        """Test that nested components cannot be accessed directly."""
        pytest.skip("TODO: Need proper nested component fixture")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

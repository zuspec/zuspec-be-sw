"""
Tests for C runtime callback functionality.

Tests Phase 4: Callbacks
"""

import pytest
import ctypes

# Check if backend is available
try:
    from zuspec.be.sw import (
        CallbackRegistry, register_callback, get_c_callback, unregister_callback
    )
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_callback_registry_creation():
    """Test that CallbackRegistry can be created."""
    registry = CallbackRegistry()
    assert registry is not None


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_register_simple_callback():
    """Test registering a simple callback."""
    registry = CallbackRegistry()
    
    # Define a simple callback
    def my_callback(x: int) -> int:
        return x * 2
    
    # Register it
    callback_id = registry.register(my_callback, [ctypes.c_int, ctypes.c_int])
    assert callback_id > 0
    
    # Get the C wrapper
    c_func = registry.get_c_callback(callback_id)
    assert c_func is not None
    
    # Call it from Python (simulating C call)
    result = c_func(21)
    assert result == 42


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_unregister_callback():
    """Test unregistering a callback."""
    registry = CallbackRegistry()
    
    def my_callback() -> None:
        pass
    
    callback_id = registry.register(my_callback, [None])
    assert registry.get_c_callback(callback_id) is not None
    
    registry.unregister(callback_id)
    assert registry.get_c_callback(callback_id) is None


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_global_registry():
    """Test the global callback registry functions."""
    def my_callback(a: int, b: int) -> int:
        return a + b
    
    # Register using global function
    callback_id = register_callback(my_callback, [ctypes.c_int, ctypes.c_int, ctypes.c_int])
    
    # Get wrapper
    c_func = get_c_callback(callback_id)
    assert c_func is not None
    
    # Test it
    result = c_func(10, 32)
    assert result == 42
    
    # Unregister
    unregister_callback(callback_id)
    assert get_c_callback(callback_id) is None


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_callback_with_no_args():
    """Test callback with no arguments."""
    registry = CallbackRegistry()
    
    called = [False]
    
    def my_callback() -> None:
        called[0] = True
    
    callback_id = registry.register(my_callback, [None])
    c_func = registry.get_c_callback(callback_id)
    
    c_func()
    assert called[0] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Basic tests for C runtime integration.

Tests Phase 1: Basic Infrastructure
"""

import pytest
import tempfile
from pathlib import Path

# Import test fixtures
from fixtures.simple_components import (
    SimpleComp, SignalComp, CompWithField, CachedComp
)

# Check if backend is available
try:
    import zuspec.dataclasses as zdc
    from zuspec.dataclasses.rt.c_rt import CObjFactory
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_c_obj_factory_creation():
    """Test that CObjFactory can be created."""
    factory = CObjFactory()
    assert factory is not None
    assert factory.cache_dir.exists()


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_simple_component_compilation():
    """Test compiling a simple component with signals."""
    # Create factory
    with tempfile.TemporaryDirectory() as tmpdir:
        factory = CObjFactory(cache_dir=Path(tmpdir), debug=True)
        
        # Create component - should compile C code
        comp = factory.mkComponent(SimpleComp)
        
        # Verify it's a proxy
        assert comp is not None
        assert hasattr(comp, '_c_lib')
        assert hasattr(comp, '_c_ptr')


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_signal_access():
    """Test accessing input/output signals through proxy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        factory = CObjFactory(cache_dir=Path(tmpdir), debug=True)
        comp = factory.mkComponent(SignalComp)
        
        # Test signal write
        comp.in_val = 42
        
        # Test signal read
        val = comp.in_val
        assert val == 42


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_field_access_denied():
    """Test that internal fields cannot be accessed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        factory = CObjFactory(cache_dir=Path(tmpdir), debug=True)
        comp = factory.mkComponent(CompWithField)
        
        # Signal should be accessible
        comp.visible_signal = 10
        assert comp.visible_signal == 10
        
        # Field should not be accessible
        with pytest.raises(AttributeError) as exc_info:
            _ = comp.internal_state
        
        assert "no accessible attribute" in str(exc_info.value).lower()


@pytest.mark.skipif(not HAS_BACKEND, reason="Backend not available")
def test_library_caching():
    """Test that compiled libraries are cached."""
    with tempfile.TemporaryDirectory() as tmpdir:
        factory = CObjFactory(cache_dir=Path(tmpdir), debug=False)
        
        # First creation - should compile
        comp1 = factory.mkComponent(CachedComp)
        assert comp1 is not None
        
        # Second creation - should use cache
        comp2 = factory.mkComponent(CachedComp)
        assert comp2 is not None
        
        # Both should use same library
        assert comp1._c_lib == comp2._c_lib


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

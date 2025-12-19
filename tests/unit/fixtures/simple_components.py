"""
Test component fixtures for C runtime testing.

These must be in a separate file so DataModelFactory can retrieve source code.
"""

import zuspec.dataclasses as zdc


@zdc.dataclass
class SimpleComp(zdc.Component):
    """Simple component with input/output signals."""
    a: zdc.bit8 = zdc.input()
    b: zdc.bit8 = zdc.input()
    result: zdc.bit8 = zdc.output()


@zdc.dataclass  
class SignalComp(zdc.Component):
    """Component for testing signal access."""
    in_val: zdc.bit16 = zdc.input()
    out_val: zdc.bit16 = zdc.output()


@zdc.dataclass
class CompWithField(zdc.Component):
    """Component with internal field (should not be accessible)."""
    internal_state: int = 0
    visible_signal: zdc.bit8 = zdc.input()


@zdc.dataclass
class CachedComp(zdc.Component):
    """Component for testing library caching."""
    val: zdc.bit8 = zdc.input()

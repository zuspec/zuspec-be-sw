"""Testbench fixtures for Topology B tests.

MemComponent wraps a zdc.Memory so it can be composed inside a parent component.
RVTestbench combines a MiniCore and a MemComponent, wiring the core's
``icache`` port to the memory's fetch function via ``__bind__``.
"""
from __future__ import annotations

import zuspec.dataclasses as zdc

from .minicore_component import MiniCore


@zdc.dataclass
class MemComponent(zdc.Component):
    """Simple memory component wrapping a 64 KiB word-addressable memory."""

    mem: zdc.Memory[zdc.uint32_t] = zdc.Memory(size=65536)


@zdc.dataclass
class RVTestbench(zdc.Component):
    """Topology-B testbench: MiniCore + MemComponent wired internally.

    The ``icache`` callable port on ``core`` is bound to ``mem``'s memory
    so instruction fetch runs entirely in generated C code.
    """

    core: MiniCore = zdc.inst()
    mem: MemComponent = zdc.inst()

    def __bind__(self):
        return {self.core.icache: self.mem}

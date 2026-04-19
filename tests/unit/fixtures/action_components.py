"""Action fixture — minimal component that uses a zdc.Action subclass.

Covers the action-inlining path in be-sw:
  - A simple ``Decode`` action with an input field and an output field.
  - ``body()`` just calls ``self.comp.icache`` and stores the result.
  - The parent process inlines the action via ``fn = await Decode(pc_in=self.pc)(comp=self)``.
"""
from __future__ import annotations

import typing
import zuspec.dataclasses as zdc


@zdc.dataclass
class Decode(zdc.Action['SimpleCore']):
    """Minimal decode action: fetch an instruction word from icache."""
    pc_in: zdc.u32 = zdc.input()
    insn32: zdc.u32 = zdc.output()

    async def body(self):
        self.insn32 = await self.comp.icache(self.pc_in)


@zdc.dataclass
class SimpleCore(zdc.Component):
    """Component that uses the Decode action in its process."""
    icache: typing.Callable[[int], typing.Awaitable[int]] = zdc.port()
    pc: zdc.u32 = zdc.field(default=0)
    last_insn: zdc.u32 = zdc.field(default=0)

    @zdc.proc
    async def run(self):
        fn: zdc.u32 = await Decode(pc_in=self.pc)(comp=self)
        self.last_insn = fn.insn32

"""MiniCore fixture — minimal RISC-V-like component for be-sw integration tests.

Covers the key field/port types present in RVCore:
  - IndexedRegFile (integer register file)
  - IndexedPool (register-rename pool)
  - Callable port (synchronous instruction-cache fetch)
  - A simple process that performs addi + ecall

This component is intentionally small so that each be-sw pass can be exercised
and validated before tackling the full RVCore.
"""
from __future__ import annotations

import typing
import zuspec.dataclasses as zdc


@zdc.dataclass
class MiniCore(zdc.Component):
    """Minimal core component for be-sw pass testing.

    Fields
    ------
    regfile:
        32-entry × 32-bit integer register file (IndexedRegFile[u5, u32]).
    rd_sched:
        Register-rename pool with 32 entries (IndexedPool[u5]).
    icache:
        Synchronous instruction-fetch callable port: (addr: int) -> int.
    pc:
        Program counter.
    halted:
        Set to True by ECALL; indicates end-of-simulation.
    """

    regfile: zdc.IndexedRegFile[zdc.u5, zdc.u32] = zdc.indexed_regfile(
        read_ports=2, write_ports=1
    )
    rd_sched: zdc.IndexedPool[zdc.u5] = zdc.indexed_pool(depth=32, noop_idx=0)
    icache: typing.Callable[[int], typing.Awaitable[int]] = zdc.port()
    pc: zdc.u32 = zdc.field(default=0)
    halted: bool = zdc.field(default=False)

    @zdc.process
    async def fetch_and_exec(self):
        """Fetch one instruction from icache and execute it (addi or ecall)."""
        instr: zdc.u32 = await self.icache(self.pc)
        opcode: int = instr & 0x7F

        if opcode == 0x13:
            # ADDI rd, rs1, imm
            rd: int  = (instr >> 7) & 0x1F
            rs1: int = (instr >> 15) & 0x1F
            imm: int = (instr >> 20)
            # sign-extend imm12
            if imm & 0x800:
                imm |= ~0xFFF
            async with self.regfile.write(rd) as wr:
                async with self.regfile.read(rs1) as r1:
                    wr.set(r1.get() + imm)
            self.pc = (self.pc + 4) & 0xFFFF_FFFF

        elif opcode == 0x73 and (instr >> 20) == 0:
            # ECALL
            self.halted = True

        else:
            # Unsupported → advance PC
            self.pc = (self.pc + 4) & 0xFFFF_FFFF

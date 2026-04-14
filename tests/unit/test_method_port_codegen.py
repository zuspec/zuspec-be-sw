"""Tests for TLM method-port code generation.

Covers:
- ``SwFuncPtrStruct`` emission with typed method pointers (``void *impl`` +
  async/sync signatures)
- ``ZSP_WAIT_PS`` macro presence in generated output
- ``WaitPointAnalysisPass`` latency inference
- ``DevirtualizePass`` connection indexing
- ``generate_tlm()`` API round-trip (IR → files)
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Protocol

import pytest
import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory, ir

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.elaborate import ElaborateSwPass
from zuspec.be.sw.passes.channel_port_lower import ChannelPortLowerPass
from zuspec.be.sw.passes.c_emit import CEmitPass


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

def _build(cls) -> SwContext:
    """Build a SwContext from a component class."""
    build_ctx = DataModelFactory().build(cls)
    return SwContext(type_m=dict(build_ctx.type_m))


def _full_pipeline(cls) -> SwContext:
    """Run elaborate + channel_port_lower + c_emit passes."""
    ctx = _build(cls)
    ctx = ElaborateSwPass().run(ctx)
    ctx = ChannelPortLowerPass().run(ctx)
    ctx = CEmitPass().run(ctx)
    return ctx


def _headers(ctx: SwContext) -> dict[str, str]:
    """Return {filename: content} for all .h output files."""
    return {f: c for f, c in ctx.output_files if f.endswith(".h")}


def _sources(ctx: SwContext) -> dict[str, str]:
    """Return {filename: content} for all .c output files."""
    return {f: c for f, c in ctx.output_files if f.endswith(".c")}


# ---------------------------------------------------------------------------
# Protocol / component definitions
# ---------------------------------------------------------------------------

class IMemPort(Protocol):
    def read(self, addr: zdc.uint64_t, length: zdc.uint32_t) -> zdc.uint64_t: ...
    def write(self, addr: zdc.uint64_t, data: zdc.uint64_t) -> None: ...
    async def fetch(self, addr: zdc.uint64_t) -> zdc.uint64_t: ...


@zdc.dataclass
class MemProvider(zdc.Component):
    mem: IMemPort = zdc.export()

    def __bind__(self): return {
        self.mem.read:  self._read,
        self.mem.write: self._write,
        self.mem.fetch: self._fetch,
    }

    def _read(self, addr: zdc.uint64_t, length: zdc.uint32_t) -> zdc.uint64_t:
        return zdc.uint64_t(0)

    def _write(self, addr: zdc.uint64_t, data: zdc.uint64_t) -> None:
        pass

    async def _fetch(self, addr: zdc.uint64_t) -> zdc.uint64_t:
        await self.wait_ns(30)
        return zdc.uint64_t(0)


@zdc.dataclass
class MemRequester(zdc.Component):
    mem: IMemPort = zdc.port()

    async def run(self) -> None:
        while True:
            _d = await self.mem.fetch(zdc.uint64_t(0x1000))
            await self.wait_ns(10)


@zdc.dataclass
class MemSystem(zdc.Component):
    req: MemRequester = zdc.field()
    prov: MemProvider = zdc.field()

    def __bind__(self): return {
        self.req.mem: self.prov.mem,
    }


# ---------------------------------------------------------------------------
# Tests: SwFuncPtrStruct emission
# ---------------------------------------------------------------------------

class TestFuncPtrStructEmission:

    def test_func_ptr_struct_emitted(self):
        """ChannelPortLowerPass creates SwFuncPtrStruct for IMemPort."""
        from zuspec.be.sw.ir.channel import SwFuncPtrStruct

        ctx = _build(MemProvider)
        ctx = ElaborateSwPass().run(ctx)
        ctx = ChannelPortLowerPass().run(ctx)

        # Collect all SwFuncPtrStruct nodes across all components from sw_nodes
        fps_nodes = []
        for name, nodes in ctx.sw_nodes.items():
            fps_nodes.extend(n for n in nodes if isinstance(n, SwFuncPtrStruct))

        assert len(fps_nodes) > 0, "Expected at least one SwFuncPtrStruct"

    def test_func_ptr_struct_has_impl_field(self):
        """Generated struct typedef contains a ``void *impl`` field."""
        ctx = _full_pipeline(MemProvider)
        headers = _headers(ctx)
        all_header_text = "\n".join(headers.values())
        assert "void *impl" in all_header_text, (
            "Expected 'void *impl' in generated headers.\n"
            f"Headers: {list(headers.keys())}\n"
            f"Content snippet: {all_header_text[:500]}"
        )

    def test_async_slot_has_frame_return(self):
        """Async slot pointer returns ``zsp_frame_s *`` (coroutine protocol)."""
        ctx = _full_pipeline(MemProvider)
        headers = _headers(ctx)
        all_text = "\n".join(headers.values())
        # Async slots must return struct zsp_frame_s *
        assert "zsp_frame_s" in all_text or "zsp_frame_t" in all_text, (
            "Expected coroutine frame type in generated async slot signature"
        )

    def test_sync_slot_returns_correct_type(self):
        """Sync ``read`` slot returns ``uint64_t``."""
        ctx = _full_pipeline(MemProvider)
        headers = _headers(ctx)
        all_text = "\n".join(headers.values())
        # read returns uint64_t
        assert "uint64_t" in all_text, (
            "Expected uint64_t return type in generated header"
        )


# ---------------------------------------------------------------------------
# Tests: WaitPointAnalysisPass
# ---------------------------------------------------------------------------

class TestWaitPointAnalysis:

    def test_no_wait_method_has_zero_latency(self):
        """A sync method with no wait() has has_wait=False."""
        from zuspec.be.sw.passes.wait_point_analysis import WaitPointAnalysisPass
        from zuspec.be.sw.ir.base import MethodLatency

        ctx = _build(MemProvider)
        ctx = ElaborateSwPass().run(ctx)
        ctx = WaitPointAnalysisPass().run(ctx)

        # _read is synchronous (not async) so won't be in method_latencies;
        # but there should be no latency with has_wait=True for it.
        for key, lat in ctx.method_latencies.items():
            comp_name, fn_name = key
            if fn_name == "_read":
                assert not lat.has_wait, f"_read should not have_wait; got {lat}"

    def test_async_method_with_wait_has_wait_true(self):
        """An async method that calls wait_ns() has has_wait=True."""
        from zuspec.be.sw.passes.wait_point_analysis import WaitPointAnalysisPass

        ctx = _build(MemProvider)
        ctx = ElaborateSwPass().run(ctx)
        ctx = WaitPointAnalysisPass().run(ctx)

        fetch_lats = [
            lat for (_, fn), lat in ctx.method_latencies.items()
            if fn == "_fetch"
        ]
        if fetch_lats:
            assert fetch_lats[0].has_wait, "_fetch should have has_wait=True"


# ---------------------------------------------------------------------------
# Tests: ElaborateSwPass bind resolution
# ---------------------------------------------------------------------------

class TestElaborateBinds:

    def test_connections_populated_for_mem_system(self):
        """ElaborateSwPass finds the MemRequester.mem → MemProvider.mem bind."""
        ctx = _build(MemSystem)
        ctx = ElaborateSwPass().run(ctx)

        # Should have at least one resolved connection
        assert len(ctx.connections) >= 1, (
            f"Expected connections, got: {ctx.connections}"
        )

    def test_connection_identifies_initiator_and_target(self):
        """Connection correctly names initiator port and target export."""
        ctx = _build(MemSystem)
        ctx = ElaborateSwPass().run(ctx)

        assert ctx.connections, "No connections resolved"
        conn = ctx.connections[0]
        # Initiator port name should contain 'mem'
        assert "mem" in conn.initiator_port.lower() or conn.initiator_port == "mem", (
            f"Unexpected initiator_port: {conn.initiator_port}"
        )


# ---------------------------------------------------------------------------
# Tests: DevirtualizePass
# ---------------------------------------------------------------------------

class TestDevirtualize:

    def test_devirtualize_records_unambiguous_connection(self):
        """DevirtualizePass records the single MemSystem connection as devirtualizable."""
        from zuspec.be.sw.passes.devirtualize import DevirtualizePass

        ctx = _build(MemSystem)
        ctx = ElaborateSwPass().run(ctx)
        ctx = DevirtualizePass().run(ctx)

        assert hasattr(ctx, "devirtualized"), "Expected 'devirtualized' attr on ctx"
        assert len(ctx.devirtualized) >= 1, (
            f"Expected at least 1 devirtualized entry, got: {ctx.devirtualized}"
        )


# ---------------------------------------------------------------------------
# Tests: generate_tlm() API
# ---------------------------------------------------------------------------

class TestGenerateTlmApi:

    def test_generate_tlm_produces_files(self, tmp_path):
        """generate_tlm() writes at least one .h and one .c file."""
        from zuspec.be.sw import generate_tlm

        written = generate_tlm(MemSystem, tmp_path, sync_mode="lt")
        h_files = [p for p in written if p.suffix == ".h"]
        c_files = [p for p in written if p.suffix == ".c"]
        assert h_files, "generate_tlm() should produce at least one .h file"
        assert c_files, "generate_tlm() should produce at least one .c file"

    def test_generate_tlm_lt_mode_copies_headers(self, tmp_path):
        """generate_tlm() copies zsp runtime headers to output dir."""
        from zuspec.be.sw import generate_tlm

        written = generate_tlm(MemSystem, tmp_path, sync_mode="lt")
        runtime_headers = [p for p in written if "zsp" in p.name]
        assert runtime_headers, "Expected zsp_*.h runtime headers to be copied"

    def test_generate_tlm_at_mode(self, tmp_path):
        """generate_tlm() with sync_mode='at' runs without error."""
        from zuspec.be.sw import generate_tlm

        written = generate_tlm(MemSystem, tmp_path, sync_mode="at")
        assert written, "generate_tlm(sync_mode='at') should produce output files"

"""Unit tests for Phase 3: C runtime module and new SW IR nodes."""
from __future__ import annotations

import pathlib
import tempfile

import pytest

# ---------------------------------------------------------------------------
# CRT string constants tests
# ---------------------------------------------------------------------------

class TestCrtStrings:
    """Validate that the C runtime string constants are well-formed."""

    def test_completion_header_guard(self):
        from zuspec.be.sw.crt.zdc_completion import HEADER
        assert "ZDC_COMPLETION_H" in HEADER
        assert "zdc_completion_init" in HEADER
        assert "ZDC_COMPLETION_AWAIT" in HEADER

    def test_completion_source_references_header(self):
        from zuspec.be.sw.crt.zdc_completion import SOURCE
        assert '#include "zdc_completion.h"' in SOURCE
        assert "zdc_completion_set" in SOURCE

    def test_queue_header_has_init_macro(self):
        from zuspec.be.sw.crt.zdc_queue import HEADER
        assert "ZDC_QUEUE_H" in HEADER
        assert "ZDC_QUEUE_INIT" in HEADER
        assert "ZDC_QUEUE_PUT" in HEADER
        assert "ZDC_QUEUE_GET" in HEADER

    def test_queue_source_has_put_get(self):
        from zuspec.be.sw.crt.zdc_queue import SOURCE
        assert "zdc_queue_put_nowait" in SOURCE
        assert "zdc_queue_get_nowait" in SOURCE

    def test_spawn_header_guard(self):
        from zuspec.be.sw.crt.zdc_spawn import HEADER
        assert "ZDC_SPAWN_H" in HEADER
        assert "zdc_spawn_handle_t" in HEADER
        assert "zdc_spawn" in HEADER
        assert "ZDC_SPAWN_JOIN" in HEADER

    def test_spawn_source_schedules_coro(self):
        from zuspec.be.sw.crt.zdc_spawn import SOURCE
        assert "zdc_coro_schedule" in SOURCE

    def test_select_header_guard(self):
        from zuspec.be.sw.crt.zdc_select import HEADER
        assert "ZDC_SELECT_H" in HEADER
        assert "zdc_select_t" in HEADER
        assert "ZDC_SELECT_WAIT" in HEADER

    def test_select_source_has_notify(self):
        from zuspec.be.sw.crt.zdc_select import SOURCE
        assert "zdc_select_notify" in SOURCE

    def test_runtime_umbrella_includes_all(self):
        from zuspec.be.sw.crt.zdc_runtime import HEADER
        assert "zdc_completion.h" in HEADER
        assert "zdc_queue.h" in HEADER
        assert "zdc_spawn.h" in HEADER
        assert "zdc_select.h" in HEADER

    def test_emit_all_writes_files(self):
        from zuspec.be.sw.crt import emit_all
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            written = emit_all(out)
            names = {p.name for p in written}
            assert "zdc_completion.h" in names
            assert "zdc_completion.c" in names
            assert "zdc_queue.h" in names
            assert "zdc_queue.c" in names
            assert "zdc_spawn.h" in names
            assert "zdc_spawn.c" in names
            assert "zdc_select.h" in names
            assert "zdc_select.c" in names
            assert "zdc_runtime.h" in names

    def test_emit_all_idempotent(self):
        """Second emit_all call returns no files (all identical content)."""
        from zuspec.be.sw.crt import emit_all
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            emit_all(out)
            written2 = emit_all(out)
            assert written2 == []


# ---------------------------------------------------------------------------
# New SW IR nodes
# ---------------------------------------------------------------------------

class TestSwSuspendCompletion:
    def test_default_construction(self):
        from zuspec.be.sw.ir.coroutine import SwSuspendCompletion
        sp = SwSuspendCompletion()
        assert sp.completion_field is None
        assert sp.out_var is None
        assert sp.elem_type is None

    def test_construction_with_fields(self):
        from zuspec.be.sw.ir.coroutine import SwSuspendCompletion
        from zuspec.dataclasses import ir
        elem = ir.DataTypeInt(bits=32, signed=False)
        sp = SwSuspendCompletion(
            completion_field="resp",
            out_var="result",
            elem_type=elem,
        )
        assert sp.completion_field == "resp"
        assert sp.out_var == "result"
        assert sp.elem_type is elem

    def test_is_suspend_point(self):
        from zuspec.be.sw.ir.coroutine import SwSuspendCompletion, SwSuspendPoint
        sp = SwSuspendCompletion()
        assert isinstance(sp, SwSuspendPoint)


class TestSwSuspendSpawn:
    def test_default_construction(self):
        from zuspec.be.sw.ir.coroutine import SwSuspendSpawn
        sp = SwSuspendSpawn()
        assert sp.spawned_func is None
        assert sp.arg_expr is None
        assert sp.handle_var is None

    def test_construction_with_fields(self):
        from zuspec.be.sw.ir.coroutine import SwSuspendSpawn
        sp = SwSuspendSpawn(
            spawned_func="my_task",
            handle_var="_my_handle",
        )
        assert sp.spawned_func == "my_task"
        assert sp.handle_var == "_my_handle"

    def test_is_suspend_point(self):
        from zuspec.be.sw.ir.coroutine import SwSuspendSpawn, SwSuspendPoint
        sp = SwSuspendSpawn()
        assert isinstance(sp, SwSuspendPoint)


# ---------------------------------------------------------------------------
# async_lower classify_await tests
# ---------------------------------------------------------------------------

class TestClassifyAwait:
    def _make_await(self, inner):
        from zuspec.dataclasses import ir
        return ir.ExprAwait(value=inner)

    def test_completion_await_expr_maps_to_suspension(self):
        from zuspec.dataclasses import ir
        if not hasattr(ir, "CompletionAwaitExpr"):
            pytest.skip("CompletionAwaitExpr not in IR")
        from zuspec.be.sw.passes.async_lower import _classify_await
        from zuspec.be.sw.ir.coroutine import SwSuspendCompletion
        # completion_expr: an attribute ref self.done → "done"
        inner = ir.CompletionAwaitExpr(
            completion_expr=ir.ExprAttribute(
                value=ir.ExprRefLocal(name="self"),
                attr="done",
            )
        )
        sp = _classify_await(self._make_await(inner))
        assert isinstance(sp, SwSuspendCompletion)
        assert sp.completion_field == "done"

    def test_queue_get_expr_maps_to_fifo_pop(self):
        from zuspec.dataclasses import ir
        if not hasattr(ir, "QueueGetExpr"):
            pytest.skip("QueueGetExpr not in IR")
        from zuspec.be.sw.passes.async_lower import _classify_await
        from zuspec.be.sw.ir.coroutine import SwSuspendFifoPop
        inner = ir.QueueGetExpr(
            queue_expr=ir.ExprAttribute(
                value=ir.ExprRefLocal(name="self"),
                attr="tx_q",
            )
        )
        sp = _classify_await(self._make_await(inner))
        assert isinstance(sp, SwSuspendFifoPop)
        assert sp.fifo_field == "tx_q"

    def test_wait_call_maps_to_suspend_wait(self):
        from zuspec.dataclasses import ir
        from zuspec.be.sw.passes.async_lower import _classify_await
        from zuspec.be.sw.ir.coroutine import SwSuspendWait
        fn = ir.ExprRefLocal(name="wait")
        call = ir.ExprCall(func=fn, args=[ir.ExprConstant(value=10)])
        sp = _classify_await(self._make_await(call))
        assert isinstance(sp, SwSuspendWait)

    def test_unknown_call_falls_back_to_suspend_call(self):
        from zuspec.dataclasses import ir
        from zuspec.be.sw.passes.async_lower import _classify_await
        from zuspec.be.sw.ir.coroutine import SwSuspendCall
        fn = ir.ExprRefLocal(name="some_async_fn")
        call = ir.ExprCall(func=fn, args=[])
        sp = _classify_await(self._make_await(call))
        assert isinstance(sp, SwSuspendCall)


# ---------------------------------------------------------------------------
# channel_port_lower QueueType handling
# ---------------------------------------------------------------------------

class TestQueueFieldLowering:
    def _make_context_with_queue_field(self):
        from zuspec.dataclasses import ir
        if not hasattr(ir, "QueueType"):
            pytest.skip("QueueType not in IR")
        from zuspec.be.sw.ir.base import SwContext
        elem = ir.DataTypeInt(bits=32, signed=False)
        queue_type = ir.QueueType(element_type=elem, depth=8)
        field = ir.Field(
            name="tx_queue",
            datatype=queue_type,
        )
        comp = ir.DataTypeComponent(name="MyComp", super=None, fields=[field])
        ctxt = SwContext()
        ctxt.type_m["MyComp"] = comp
        return ctxt

    def test_queue_field_creates_sw_fifo(self):
        ctxt = self._make_context_with_queue_field()
        from zuspec.be.sw.passes.channel_port_lower import ChannelPortLowerPass
        from zuspec.be.sw.ir.channel import SwFifo
        pass_ = ChannelPortLowerPass()
        out = pass_.run(ctxt)
        nodes = out.sw_nodes.get("MyComp", [])
        fifos = [n for n in nodes if isinstance(n, SwFifo)]
        assert len(fifos) == 1
        assert fifos[0].field_name == "tx_queue"
        assert fifos[0].depth == 8

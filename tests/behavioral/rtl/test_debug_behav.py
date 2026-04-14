"""Behavioral debug layer tests: coroutine frame registry (Phase B).

Tests:
  - B1: debug struct fields appear in generated C header
  - B3: _co_src_file/_co_src_line assigned at suspension points
  - B4: zsp_push_frame/zsp_pop_frame emitted in co_run
  - End-to-end: debug=True compile of behavioral component succeeds
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import zuspec.dataclasses as zdc
from zuspec.dataclasses import DataModelFactory

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.rtl.component_classify import ComponentClassifyPass
from zuspec.be.sw.passes.rtl.next_state_split import NextStateSplitPass
from zuspec.be.sw.passes.rtl.comb_order import CombTopoSortPass
from zuspec.be.sw.passes.rtl.expr_lower import ExprLowerPass
from zuspec.be.sw.passes.rtl.c_emit import RtlCEmitPass as CEmitPass

_EXAMPLES = Path(__file__).parents[5] / "examples"


def _load_class(subdir, module, classname):
    ex_dir = str(_EXAMPLES / subdir)
    if ex_dir not in sys.path:
        sys.path.insert(0, ex_dir)
    import importlib
    mod = importlib.import_module(module)
    return getattr(mod, classname)


def _build(py_cls):
    ctx = DataModelFactory().build(py_cls)
    return ctx.type_m[py_cls.__qualname__]


def _run_pipeline_behav(py_cls, rtl_debug: bool = False) -> SwContext:
    from zuspec.be.sw.passes.rtl.wait_lower import WaitLowerPass
    from zuspec.be.sw.passes.rtl.pipeline_lower import PipelineLowerPass
    import sys
    dmf = DataModelFactory()
    build_ctx = dmf.build(py_cls)
    comp_ir = build_ctx.type_m[py_cls.__qualname__]
    _mod = sys.modules.get(py_cls.__module__, None)
    _module_globals = _mod.__dict__ if _mod is not None else {}
    ctx = SwContext(type_m=build_ctx.type_m)
    ctx.rtl_component = comp_ir
    ctx.rtl_debug = rtl_debug
    ctx.rtl_domain_period_ps = 10_000
    ctx.py_globals = _module_globals
    ctx.rtl_component_class = py_cls
    for cls in [ComponentClassifyPass, NextStateSplitPass, CombTopoSortPass,
                ExprLowerPass, PipelineLowerPass, WaitLowerPass, CEmitPass]:
        ctx = cls().run(ctx)
    return ctx


def _get_file(ctx: SwContext, suffix: str) -> str:
    for name, content in ctx.output_files:
        if name.endswith(suffix):
            return content
    pytest.fail(f"No file with suffix {suffix!r} in output_files")


@pytest.fixture(scope="module")
def DelayCounter():
    return _load_class("06_delay_counter", "delay_counter", "DelayCounter")


# ---------------------------------------------------------------------------
# B1: debug struct fields in generated C header
# ---------------------------------------------------------------------------

class TestBehavDebugStructFields:
    """B1: debug coroutine fields appear in header iff debug=True."""

    def test_debug_false_no_co_frame(self, DelayCounter):
        ctx = _run_pipeline_behav(DelayCounter, rtl_debug=False)
        h = _get_file(ctx, ".h")
        assert "_co_frame" not in h
        assert "_co_src_file" not in h

    def test_debug_true_has_co_src_file(self, DelayCounter):
        ctx = _run_pipeline_behav(DelayCounter, rtl_debug=True)
        h = _get_file(ctx, ".h")
        assert "_co_src_file" in h, "Expected _co_src_file field in debug header"
        assert "_co_src_line" in h
        assert "_co_name" in h
        assert "_co_frame" in h

    def test_debug_true_has_ZspCoroFrame_type(self, DelayCounter):
        ctx = _run_pipeline_behav(DelayCounter, rtl_debug=True)
        h = _get_file(ctx, ".h")
        assert "ZspCoroFrame_t" in h


# ---------------------------------------------------------------------------
# B3: _co_src_file/_co_src_line assigned at suspension points
# ---------------------------------------------------------------------------

class TestBehavSuspensionLoc:
    """B3: generated co_run should set _co_src_file/_co_src_line before return."""

    def test_debug_true_has_co_src_file_assignment(self, DelayCounter):
        ctx = _run_pipeline_behav(DelayCounter, rtl_debug=True)
        c = _get_file(ctx, ".c")
        assert "self->_co_src_file" in c, (
            "Expected 'self->_co_src_file = ...' in behavioral .c with debug=True"
        )
        assert "self->_co_src_line" in c

    def test_debug_false_no_co_src_file_assignment(self, DelayCounter):
        ctx = _run_pipeline_behav(DelayCounter, rtl_debug=False)
        c = _get_file(ctx, ".c")
        assert "self->_co_src_file" not in c


# ---------------------------------------------------------------------------
# B4: zsp_push_frame / zsp_pop_frame in co_run
# ---------------------------------------------------------------------------

class TestBehavFramePushPop:
    """B4: zsp_push_frame/zsp_pop_frame must bracket co_run when debug=True."""

    def test_debug_true_has_push_frame(self, DelayCounter):
        ctx = _run_pipeline_behav(DelayCounter, rtl_debug=True)
        c = _get_file(ctx, ".c")
        assert "zsp_push_frame" in c, "Expected zsp_push_frame in co_run"
        assert "zsp_pop_frame" in c, "Expected zsp_pop_frame in co_run"

    def test_debug_false_no_push_frame(self, DelayCounter):
        ctx = _run_pipeline_behav(DelayCounter, rtl_debug=False)
        c = _get_file(ctx, ".c")
        assert "zsp_push_frame" not in c
        assert "zsp_pop_frame" not in c


# ---------------------------------------------------------------------------
# End-to-end: compile_and_load(debug=True) on behavioral component
# ---------------------------------------------------------------------------

class TestBehavDebugCompile:
    """Behavioral component with debug=True compiles and runs correctly."""

    def test_compile_so_debug_behavioral(self, DelayCounter):
        from zuspec.be.sw import compile_and_load
        with tempfile.TemporaryDirectory() as td:
            lib, State = compile_and_load(
                DelayCounter, td,
                debug=True,
                domain_period_ps=10_000,
            )
            assert isinstance(lib, ctypes.CDLL)
            s = State()
            lib.DelayCounter_init.argtypes = [ctypes.POINTER(State)]
            lib.DelayCounter_init.restype = None
            lib.DelayCounter_init(ctypes.byref(s))
            # Verify behavioral execution still produces correct results
            s.delay = 5
            lib.DelayCounter_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]
            lib.DelayCounter_sim_run.restype = None
            lib.DelayCounter_sim_run(ctypes.byref(s), 5)
            assert s.count == 1, f"Expected count=1 after 5 cycles with delay=5, got {s.count}"

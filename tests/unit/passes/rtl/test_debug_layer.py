"""Unit tests for the debug layer (Layers 0-2) of the C debug system.

Covers:
  - A2: loc propagation onto IR Stmt* nodes from DataModelFactory
  - A3/A4/A5: #line directive emission in generated C (sync, comb, behavioral)
  - A1: debug flag threading through generate() / compile_and_load()
  - A6/B2: zsp_rtl_debug.h / zsp_rtl_debug.c presence in rt/
"""
from __future__ import annotations

import re
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build(py_cls):
    ctx = DataModelFactory().build(py_cls)
    return ctx.type_m[py_cls.__qualname__]


def _run_pipeline(py_cls, rtl_debug: bool = False) -> SwContext:
    comp = _build(py_cls)
    ctx = SwContext(rtl_component=comp, rtl_debug=rtl_debug)
    for cls in [ComponentClassifyPass, NextStateSplitPass, CombTopoSortPass,
                ExprLowerPass, CEmitPass]:
        ctx = cls().run(ctx)
    return ctx


def _get_file(ctx: SwContext, suffix: str) -> str:
    for name, content in ctx.output_files:
        if name.endswith(suffix):
            return content
    pytest.fail(f"No file with suffix {suffix!r} in output_files")


# ---------------------------------------------------------------------------
# A2: loc propagation
# ---------------------------------------------------------------------------

class TestLocPropagation:
    """IR Stmt* nodes should carry loc after DataModelFactory.build()."""

    def test_sync_stmts_have_loc(self):
        @zdc.dataclass
        class LocCounter(zdc.Component):
            clock: zdc.bit = zdc.input()
            reset: zdc.bit = zdc.input()
            count: zdc.b32 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
            def _count(self):
                if self.reset:
                    self.count = 0
                else:
                    self.count = self.count + 1

        comp = _build(LocCounter)
        proc = comp.sync_processes[0]
        stmts_with_loc = [s for s in proc.body if getattr(s, 'loc', None) is not None]
        assert stmts_with_loc, "Expected at least one Stmt with loc in @sync body"

    def test_loc_file_is_this_file(self):
        @zdc.dataclass
        class LocSimple(zdc.Component):
            clock: zdc.bit = zdc.input()
            val: zdc.b8 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _set(self):
                self.val = 42

        comp = _build(LocSimple)
        proc = comp.sync_processes[0]
        locs = [s.loc for s in proc.body if getattr(s, 'loc', None) is not None]
        assert locs, "No loc found on sync stmts"
        # The file should point to *this* test file (or the file where the class is defined)
        for loc in locs:
            assert loc.file is not None
            assert loc.line > 0

    def test_loc_line_number_is_positive(self):
        @zdc.dataclass
        class LocLine(zdc.Component):
            clock: zdc.bit = zdc.input()
            x: zdc.b16 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _proc(self):
                self.x = 0xFF

        comp = _build(LocLine)
        proc = comp.sync_processes[0]
        for s in proc.body:
            loc = getattr(s, 'loc', None)
            if loc is not None:
                assert loc.line > 0, f"loc.line should be positive, got {loc.line}"


# ---------------------------------------------------------------------------
# A3/A4: #line in generated C — sync bodies
# ---------------------------------------------------------------------------

class TestLineDirectivesSync:
    """With debug=True, generated .c should contain #line directives."""

    def test_debug_false_no_line_directives(self):
        @zdc.dataclass
        class NdCounter(zdc.Component):
            clock: zdc.bit = zdc.input()
            count: zdc.b32 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _count(self):
                self.count = self.count + 1

        ctx = _run_pipeline(NdCounter, rtl_debug=False)
        c_src = _get_file(ctx, ".c")
        assert "#line" not in c_src, "No #line directives expected when debug=False"

    def test_debug_true_has_line_directives(self):
        @zdc.dataclass
        class DbgCounter(zdc.Component):
            clock: zdc.bit = zdc.input()
            count: zdc.b32 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _count(self):
                self.count = self.count + 1

        ctx = _run_pipeline(DbgCounter, rtl_debug=True)
        c_src = _get_file(ctx, ".c")
        assert "#line" in c_src, "#line directives expected in .c when debug=True"

    def test_line_directive_format(self):
        @zdc.dataclass
        class FmtCounter(zdc.Component):
            clock: zdc.bit = zdc.input()
            count: zdc.b32 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _count(self):
                self.count = self.count + 1

        ctx = _run_pipeline(FmtCounter, rtl_debug=True)
        c_src = _get_file(ctx, ".c")
        # #line N "file" format
        line_directives = re.findall(r'#line\s+(\d+)\s+"([^"]+)"', c_src)
        assert line_directives, "No well-formed #line directives found"
        for lineno_str, filepath in line_directives:
            assert int(lineno_str) > 0
            assert filepath.endswith(".py")

    def test_debug_true_header_includes_debug_h(self):
        @zdc.dataclass
        class DbgHdr(zdc.Component):
            clock: zdc.bit = zdc.input()
            x: zdc.b8 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _proc(self):
                self.x = 0

        ctx = _run_pipeline(DbgHdr, rtl_debug=True)
        h_src = _get_file(ctx, ".h")
        assert 'zsp_rtl_debug.h' in h_src, "Header should include zsp_rtl_debug.h when debug=True"

    def test_debug_false_header_no_debug_h(self):
        @zdc.dataclass
        class NdHdr(zdc.Component):
            clock: zdc.bit = zdc.input()
            x: zdc.b8 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _proc(self):
                self.x = 0

        ctx = _run_pipeline(NdHdr, rtl_debug=False)
        h_src = _get_file(ctx, ".h")
        assert 'zsp_rtl_debug.h' not in h_src


# ---------------------------------------------------------------------------
# A5: #line in comb bodies
# ---------------------------------------------------------------------------

class TestLineDirectivesComb:
    """debug=True should emit #line inside @comb bodies too."""

    def test_comb_body_has_line_directives(self):
        @zdc.dataclass
        class CombDbg(zdc.Component):
            clock: zdc.bit = zdc.input()
            a: zdc.b8 = zdc.input()
            b: zdc.b8 = zdc.input()
            c: zdc.b8 = zdc.output()

            @zdc.comb
            def _compute(self):
                self.c = self.a + self.b

        ctx = _run_pipeline(CombDbg, rtl_debug=True)
        c_src = _get_file(ctx, ".c")
        assert "#line" in c_src


# ---------------------------------------------------------------------------
# A6 / B2: Runtime debug header and .c file existence
# ---------------------------------------------------------------------------

class TestDebugRtFiles:
    """zsp_rtl_debug.h and zsp_rtl_debug.c must exist in the rt/ directory."""

    def test_debug_header_exists(self):
        import zuspec.be.sw as _zsp_be_sw
        hdr = Path(_zsp_be_sw.__file__).parent / "share" / "include" / "zsp_rtl_debug.h"
        assert hdr.exists(), f"zsp_rtl_debug.h not found at {hdr}"

    def test_debug_c_exists(self):
        import zuspec.be.sw as _zsp_be_sw
        src = Path(_zsp_be_sw.__file__).parent / "share" / "rt" / "zsp_rtl_debug.c"
        assert src.exists(), f"zsp_rtl_debug.c not found at {src}"

    def test_debug_header_contains_zsp_coro_top(self):
        import zuspec.be.sw as _zsp_be_sw
        hdr = Path(_zsp_be_sw.__file__).parent / "share" / "include" / "zsp_rtl_debug.h"
        content = hdr.read_text()
        assert "zsp_coro_top" in content

    def test_debug_header_contains_ZS_LOC_macro(self):
        import zuspec.be.sw as _zsp_be_sw
        hdr = Path(_zsp_be_sw.__file__).parent / "share" / "include" / "zsp_rtl_debug.h"
        content = hdr.read_text()
        assert "ZS_LOC" in content

    def test_debug_c_defines_zsp_coro_top(self):
        import zuspec.be.sw as _zsp_be_sw
        src = Path(_zsp_be_sw.__file__).parent / "share" / "rt" / "zsp_rtl_debug.c"
        content = src.read_text()
        assert "zsp_coro_top" in content


# ---------------------------------------------------------------------------
# A1: debug flag threading
# ---------------------------------------------------------------------------

class TestDebugFlagAPI:
    """SwContext.debug and generate()/compile_and_load() debug parameter."""

    def test_rtl_context_debug_default_false(self):
        @zdc.dataclass
        class _Dummy(zdc.Component):
            clock: zdc.bit = zdc.input()

        comp = _build(_Dummy)
        ctx = SwContext(rtl_component=comp)
        assert ctx.rtl_debug is False

    def test_rtl_context_debug_true(self):
        @zdc.dataclass
        class _Dummy2(zdc.Component):
            clock: zdc.bit = zdc.input()

        comp = _build(_Dummy2)
        ctx = SwContext(rtl_component=comp, rtl_debug=True)
        assert ctx.rtl_debug is True

    def test_generate_accepts_debug_param(self):
        """generate() should accept debug kwarg without error."""
        from zuspec.be.sw import generate

        @zdc.dataclass
        class _GenComp(zdc.Component):
            clock: zdc.bit = zdc.input()
            x: zdc.b8 = zdc.output()

            @zdc.sync(clock=lambda s: s.clock)
            def _proc(self):
                self.x = 0

        with tempfile.TemporaryDirectory() as td:
            paths = generate(_GenComp, td, debug=True)
            assert paths  # non-empty

    def test_compile_so_debug_produces_so(self):
        """compile_and_load(debug=True) should succeed and produce a .so."""
        import sys
        import ctypes
        from pathlib import Path
        from zuspec.be.sw import compile_and_load

        examples = Path(__file__).parents[6] / "examples" / "01_counter"
        if str(examples) not in sys.path:
            sys.path.insert(0, str(examples))
        import counter as _mod
        CounterCls = _mod.Counter

        with tempfile.TemporaryDirectory() as td:
            lib, State = compile_and_load(CounterCls, td, debug=True)
            assert isinstance(lib, ctypes.CDLL)


# ---------------------------------------------------------------------------
# C1: _build_srcmap — JSON schema validation
# ---------------------------------------------------------------------------

class TestBuildSrcmap:
    """CEmitPass._build_srcmap() must produce well-formed JSON."""

    def _run_debug(self, py_cls) -> SwContext:
        from zuspec.be.sw.passes.rtl.pipeline_lower import PipelineLowerPass
        from zuspec.be.sw.passes.rtl.wait_lower import WaitLowerPass
        comp = _build(py_cls)
        ctx = SwContext(rtl_component=comp, rtl_debug=True)
        for cls in [ComponentClassifyPass, NextStateSplitPass, CombTopoSortPass,
                    ExprLowerPass, CEmitPass]:
            ctx = cls().run(ctx)
        return ctx

    def test_srcmap_json_valid(self):
        """debug=True output_files must contain a _srcmap.c with valid JSON."""
        import json as _json

        @zdc.dataclass
        class SrcmapComp(zdc.Component):
            clock: zdc.bit = zdc.input()
            x: zdc.uint8_t = zdc.field(default=0)

            @zdc.sync(clock=lambda s: s.clock)
            def proc(self):
                self.x = self.x + 1

        ctx = self._run_debug(SrcmapComp)
        srcmap_c = _get_file(ctx, "_srcmap.c")
        # Extract the JSON string from the C source
        m = re.search(r'"(\{.*\})"', srcmap_c, re.DOTALL)
        assert m is not None, "No JSON object found in _srcmap.c"
        # Unescape C escapes
        raw = m.group(1).replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        sm = _json.loads(raw)
        assert sm["version"] == 1
        assert "SrcmapComp" in sm["component"]
        assert "SrcmapComp" in sm["c_type"]
        assert isinstance(sm["fields"], list)
        assert isinstance(sm["nxt_fields"], list)
        assert isinstance(sm["processes"], list)

    def test_srcmap_fields_schema(self):
        """Each field entry must have src_name, c_name, width, signed, kind."""
        import json as _json

        @zdc.dataclass
        class SchemaComp(zdc.Component):
            clock:  zdc.bit    = zdc.input()
            count:  zdc.uint16_t = zdc.field(default=0)
            flag:   zdc.uint8_t  = zdc.field(default=0)

            @zdc.sync(clock=lambda s: s.clock)
            def proc(self):
                self.count = self.count + 1

        ctx = self._run_debug(SchemaComp)
        srcmap_c = _get_file(ctx, "_srcmap.c")
        m = re.search(r'"(\{.*\})"', srcmap_c, re.DOTALL)
        assert m is not None
        raw = m.group(1).replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        sm = _json.loads(raw)
        names = {f["src_name"] for f in sm["fields"]}
        assert "count" in names
        assert "flag"  in names
        for fd in sm["fields"]:
            assert "src_name" in fd
            assert "c_name"   in fd
            assert "width"    in fd
            assert "signed"   in fd
            assert "kind"     in fd

    def test_srcmap_has_debug_coro_fields(self):
        """coro_fields must include debug frame members for behavioral comps."""
        import json as _json

        @zdc.dataclass
        class CoroSrcmapComp(zdc.Component):
            clock: zdc.bit = zdc.input()
            count: zdc.uint8_t = zdc.field(default=0)

            @zdc.sync(clock=lambda s: s.clock)
            def proc(self):
                self.count = self.count + 1

        ctx = self._run_debug(CoroSrcmapComp)
        srcmap_c = _get_file(ctx, "_srcmap.c")
        assert "_co_src_file" in srcmap_c
        assert "_co_src_line" in srcmap_c
        assert "_co_frame"    in srcmap_c


# ---------------------------------------------------------------------------
# C2: _emit_srcmap_c and _emit_debug_c
# ---------------------------------------------------------------------------

class TestEmitSrcmapC:
    """_emit_srcmap_c() must produce valid C with ELF section attribute."""

    def test_section_attribute_present(self):
        emit = CEmitPass()
        c_src = emit._emit_srcmap_c("Foo", '{"version": 1}')
        assert '.zuspec_srcmap' in c_src
        assert '__attribute__' in c_src
        assert 'ZS_DEBUG' in c_src

    def test_json_content_embedded(self):
        emit = CEmitPass()
        payload = '{"version": 1, "component": "Bar"}'
        c_src = emit._emit_srcmap_c("Bar", payload)
        # version key must appear (possibly with C-escaped quotes)
        assert "version" in c_src
        assert "Bar" in c_src


class TestEmitDebugC:
    """_emit_debug_c() must embed the GDB auto-load script."""

    def test_debug_gdb_scripts_section(self):
        emit = CEmitPass()
        c_src = emit._emit_debug_c("Baz")
        assert '.debug_gdb_scripts' in c_src
        assert '__attribute__' in c_src

    def test_gdb_script_type_byte(self):
        """ELF inline Python format starts with \\x04."""
        emit = CEmitPass()
        c_src = emit._emit_debug_c("Baz")
        assert '\\x04' in c_src

    def test_gdb_script_name_embedded(self):
        emit = CEmitPass()
        c_src = emit._emit_debug_c("Baz")
        assert 'zuspec_gdb' in c_src

    def test_gdb_script_content_included(self):
        """The actual GDB helper Python code must be embedded."""
        emit = CEmitPass()
        c_src = emit._emit_debug_c("Baz")
        # The GDB script defines zs-bt; check it appears
        assert 'zs-bt' in c_src or 'ZsBt' in c_src

    def test_debug_files_in_output_files(self):
        """debug=True must add _srcmap.c and _debug.c to output_files."""
        @zdc.dataclass
        class DebugFilesComp(zdc.Component):
            clock: zdc.bit = zdc.input()
            x: zdc.uint8_t = zdc.field(default=0)

            @zdc.sync(clock=lambda s: s.clock)
            def proc(self):
                self.x = self.x + 1

        ctx = _run_pipeline(DebugFilesComp, rtl_debug=True)
        suffixes = [name for name, _ in ctx.output_files]
        assert any(s.endswith("_srcmap.c") for s in suffixes), f"No _srcmap.c in {suffixes}"
        assert any(s.endswith("_debug.c")  for s in suffixes), f"No _debug.c  in {suffixes}"


# ---------------------------------------------------------------------------
# C3: zuspec_gdb.py importability and command definitions
# ---------------------------------------------------------------------------

class TestZuspecGdbModule:
    """zuspec_gdb.py must be importable outside GDB (gdb=None path)."""

    def test_import_without_gdb(self):
        import importlib.util, sys
        from pathlib import Path
        import zuspec.be.sw as _zsp_be_sw
        gdb_py = Path(_zsp_be_sw.__file__).parent / "debug" / "zuspec_gdb.py"
        spec = importlib.util.spec_from_file_location("zuspec_gdb", gdb_py)
        mod  = importlib.util.module_from_spec(spec)
        # Should not raise even without the real `gdb` module
        spec.loader.exec_module(mod)
        assert hasattr(mod, "_srcmaps")
        assert isinstance(mod._srcmaps, dict)

    def test_frame_filter_defined(self):
        import importlib.util
        from pathlib import Path
        import zuspec.be.sw as _zsp_be_sw
        gdb_py = Path(_zsp_be_sw.__file__).parent / "debug" / "zuspec_gdb.py"
        spec = importlib.util.spec_from_file_location("zuspec_gdb2", gdb_py)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "ZspFrameFilter")
        ff = mod.ZspFrameFilter()
        assert hasattr(ff, "filter")


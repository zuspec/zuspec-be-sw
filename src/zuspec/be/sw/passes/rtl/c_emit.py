"""
CEmitPass — generate .h, .c, and _ctypes.py for a component.

For a component ``Foo`` in RTL Tier 0/1 this emits:

  Foo.h          — struct Foo; function prototypes
  Foo.c          — function bodies
  Foo_ctypes.py  — ctypes Structure + argtypes bindings

The generated C follows the design documented in §4 and §5 of the plan.
"""
from __future__ import annotations

import json
import os
import textwrap
from typing import List

from zuspec.ir.core.expr import (ExprAwait, ExprCall, ExprAttribute, ExprRefField, ExprRefUnresolved,
                                         ExprConstant, AugOp)
from zuspec.ir.core.stmt import StmtWhile, StmtExpr, StmtAugAssign, StmtAssign, StmtIf
from zuspec.ir.core.data_type import DataTypeInt, DataTypeComponent, DataTypeRef, DataTypeStruct, DataTypeArray
from zuspec.ir.core.fields import SignalDirection, FieldKind

from zuspec.be.sw.ir.protocol import EvalProtocol
from zuspec.be.sw.ir.base import SwContext
from .type_mapper import RtlTypeMapper
from .expr_lower import ExprLower, collect_local_names
from .wait_lower import WaitLowerPass


_CTYPES_INT_MAP = {
    "uint8_t":  "ctypes.c_uint8",
    "uint16_t": "ctypes.c_uint16",
    "uint32_t": "ctypes.c_uint32",
    "uint64_t": "ctypes.c_uint64",
    "int8_t":   "ctypes.c_int8",
    "int16_t":  "ctypes.c_int16",
    "int32_t":  "ctypes.c_int32",
    "int64_t":  "ctypes.c_int64",
}


class RtlCEmitPass:
    """Emit .h / .c / _ctypes.py into ``ctx.output_files``."""

    def run(self, ctx: SwContext) -> SwContext:
        comp = ctx.rtl_component
        name = comp.name or "Component"
        tm = RtlTypeMapper()

        ctx.output_files = []
        ctx.output_files.append((f"{name}.h",        self._emit_header(comp, name, tm, ctx)))
        ctx.output_files.append((f"{name}.c",        self._emit_source(comp, name, tm, ctx)))
        ctx.output_files.append((f"{name}_ctypes.py", self._emit_ctypes(comp, name, tm, ctx)))
        if ctx.rtl_debug:
            srcmap_json = self._build_srcmap(comp, name, ctx)
            ctx.output_files.append((f"{name}_srcmap.c",  self._emit_srcmap_c(name, srcmap_json)))
            ctx.output_files.append((f"{name}_debug.c",   self._emit_debug_c(name)))
        return ctx

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _emit_header(self, comp, name: str, tm: RtlTypeMapper, ctx: SwContext) -> str:
        guard = f"_{name.upper()}_H"
        has_behav = bool(ctx.rtl_behav_processes)
        lines = [
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
            '#include "zsp_rtl.h"',
        ]
        if has_behav:
            lines.append('#include "zsp_rtl_harness.h"')
        if ctx.rtl_debug:
            lines.append('#include "zsp_rtl_debug.h"')
        lines += [
            "#include <stdint.h>",
            "#include <string.h>",
            "",
        ]

        # Emit embedded struct definitions for DataTypeRef fields
        lines += self._emit_embedded_structs(comp, ctx)

        # Emit the Regs sub-struct if there are any registered fields.
        # This allows advance() to be a single struct assignment.
        if ctx.rtl_nxt_fields:
            lines += self._emit_regs_substruct(comp, name, tm, ctx)

        lines += [f"typedef struct {{"]

        # Non-registered fields: comp.fields that do NOT have a _nxt shadow.
        # Emitted in comp.fields declaration order.
        for f in comp.fields:
            if f.name in ctx.rtl_nxt_fields:
                continue  # registered — emitted in the sorted block below
            if isinstance(f.datatype, DataTypeInt):
                c_type = tm.map_rtl_int_type(f.datatype)
                lines.append(f"    {c_type} {f.name};")
            elif isinstance(f.datatype, DataTypeArray):
                elem = f.datatype.element_type
                if isinstance(elem, DataTypeInt):
                    c_type = tm.map_rtl_int_type(elem)
                else:
                    c_type = "uint32_t"
                lines.append(f"    {c_type} {f.name}[{f.datatype.size}];")
            elif isinstance(f.datatype, DataTypeRef):
                struct_name = f.datatype.ref_name
                lines.append(f"    {struct_name} {f.name};")
            elif isinstance(f.datatype, DataTypeComponent):
                sub_name = f.datatype.name or "SubComp"
                lines.append(f"    {sub_name} {f.name};")
            else:
                lines.append(f"    uint32_t {f.name};  /* unknown type */")

        # Wire fields (from @property / wire_processes)
        if hasattr(comp, 'wire_processes') and comp.wire_processes:
            lines.append("    /* wire fields (computed each clock edge) */")
            for wp in comp.wire_processes:
                ret = getattr(wp, 'returns', None)
                if ret is not None and isinstance(ret, DataTypeInt):
                    c_type = tm.map_rtl_int_type(ret)
                else:
                    c_type = "uint32_t"
                lines.append(f"    {c_type} {wp.name};")

        # Registered state: embed two instances of the Regs sub-struct (_regs and _nxt).
        # advance() becomes a single struct assignment: self->_regs = self->_nxt.
        if ctx.rtl_nxt_fields:
            lines.append(f"    /* registered state (advance via struct assign) */")
            lines.append(f"    _{name}_Regs _regs;")
            lines.append(f"    _{name}_Regs _nxt;")

        # Behavioral coroutine state fields
        if has_behav:
            lines.append("    /* behavioral coroutine state */")
            lines.append("    int32_t  _co_pc;    /* -1=done, >=0=active */")
            lines.append("    zsp_ps_t _co_tick;  /* current ps timestamp */")
            lines.append("    zsp_ps_t _co_wake;  /* ps timestamp to resume */")
            if ctx.rtl_debug:
                lines.append("    /* debug: per-coroutine source location (set at each suspension) */")
                lines.append("    const char     *_co_src_file;")
                lines.append("    int32_t         _co_src_line;")
                lines.append("    const char     *_co_name;")
                lines.append("    ZspCoroFrame_t  _co_frame;")

        lines += [
            f"}} {name};",
            "",
        ]

        # Const-field macros: allow compiler to const-fold ENABLE_* etc.
        comp_cls = ctx.rtl_component_class
        const_fields = [f for f in comp.fields if f.is_const]
        if const_fields and comp_cls is not None:
            lines.append("/* const-field macros for compile-time folding */")
            for f in const_fields:
                val = getattr(comp_cls, f.name, 0)
                lines.append(f"#define {name}_{f.name} {val}U")
            lines.append("")

        lines += [
            f"void {name}_init({name} *self);",
            f"void {name}_clock_edge({name} *self);",
            f"void {name}_run_cycles({name} *self, uint64_t n);",
            f"void {name}_advance({name} *self);",
            f"void {name}_eval_comb({name} *self);",
        ]
        if self._has_domain_reset(comp):
            lines.append(f"void {name}_apply_reset({name} *self);")
        if has_behav:
            lines += [
                f"void {name}_co_run({name} *self, zsp_ps_t tick);",
                f"void {name}_sim_run({name} *self, uint64_t n_cycles);",
            ]
        lines += [
            "",
            f"#endif /* {guard} */",
        ]
        return "\n".join(lines) + "\n"

    def _emit_embedded_structs(self, comp, ctx: SwContext) -> list:
        """Emit C struct typedefs for any DataTypeRef fields."""
        lines = []
        tm = RtlTypeMapper()
        seen = set()
        for f in comp.fields:
            if not isinstance(f.datatype, DataTypeRef):
                continue
            ref_name = f.datatype.ref_name
            if ref_name in seen:
                continue
            seen.add(ref_name)
            # Look up the struct definition
            struct_def = ctx.type_m.get(ref_name)
            if struct_def is None or not hasattr(struct_def, 'fields'):
                lines.append(f"/* struct {ref_name} not found in type_m */")
                continue
            lines.append(f"typedef struct {{")
            for sf in struct_def.fields:
                if isinstance(sf.datatype, DataTypeInt):
                    c_type = tm.map_rtl_int_type(sf.datatype)
                    lines.append(f"    {c_type} {sf.name};")
                else:
                    lines.append(f"    uint32_t {sf.name};  /* unknown */")
            lines.append(f"}} {ref_name};")
            lines.append("")
        return lines

    def _type_align(self, f, tm: RtlTypeMapper) -> int:
        """Return the C alignment (bytes) of a field, for sorting purposes."""
        if isinstance(f.datatype, DataTypeInt):
            c_type = tm.map_rtl_int_type(f.datatype)
            return {"uint64_t": 8, "int64_t": 8,
                    "uint32_t": 4, "int32_t": 4,
                    "uint16_t": 2, "int16_t": 2}.get(c_type, 1)
        if isinstance(f.datatype, DataTypeRef):
            return 4  # assume struct fields have at least 4-byte alignment
        return 1

    def _sorted_regs_fields(self, comp, tm: RtlTypeMapper, ctx: SwContext) -> list:
        """Return registered fields sorted by decreasing alignment then name.

        Sorting by (alignment descending, name ascending) eliminates internal
        padding from mixed-width fields (e.g. uint8_t interleaved with uint64_t),
        minimising the _Regs struct size and the data moved by advance().
        """
        field_map = {f.name: f for f in comp.fields}
        fields = [field_map[n] for n in ctx.rtl_nxt_fields if n in field_map]
        return sorted(fields, key=lambda f: (-self._type_align(f, tm), f.name))

    def _emit_regs_substruct(self, comp, name: str, tm: RtlTypeMapper, ctx: SwContext) -> list:
        """Emit the _Name_Regs sub-struct that holds all registered fields (sorted)."""
        lines = [f"typedef struct {{"]
        for f in self._sorted_regs_fields(comp, tm, ctx):
            if isinstance(f.datatype, DataTypeInt):
                c_type = tm.map_rtl_int_type(f.datatype)
                lines.append(f"    {c_type} {f.name};")
            elif isinstance(f.datatype, DataTypeRef):
                struct_name = f.datatype.ref_name
                lines.append(f"    {struct_name} {f.name};")
            else:
                lines.append(f"    uint32_t {f.name};  /* unknown */")
        lines.append(f"}} _{name}_Regs;")
        lines.append("")
        return lines

    # ------------------------------------------------------------------
    # Source
    # ------------------------------------------------------------------

    def _emit_source(self, comp, name: str, tm: RtlTypeMapper, ctx: SwContext) -> str:
        lines = [
            f'#include "{name}.h"',
            "#include <string.h>",
            "",
        ]
        lines += self._emit_init(comp, name, tm, ctx)
        lines += [""]
        lines += self._emit_sync_bodies(comp, name, tm, ctx)
        lines += [""]
        lines += self._emit_advance(comp, name, ctx)
        lines += [""]
        lines += self._emit_clock_edge(comp, name, ctx)
        lines += [""]
        lines += self._emit_run_cycles(comp, name, ctx)
        if self._has_domain_reset(comp):
            lines += [""]
            lines += self._emit_apply_reset(comp, name, ctx)
        lines += [""]
        lines += self._emit_eval_comb(comp, name, tm, ctx)
        if ctx.rtl_behav_processes:
            lines += [""]
            lines += self._emit_co_run(comp, name, ctx)
            lines += [""]
            lines += self._emit_sim_run(comp, name, ctx)
        return "\n".join(lines) + "\n"

    def _emit_init(self, comp, name: str, tm: RtlTypeMapper, ctx: SwContext) -> List[str]:
        lines = [f"void {name}_init({name} *self) {{"]
        comp_cls = ctx.rtl_component_class
        for f in comp.fields:
            if f.name in ctx.rtl_nxt_fields:
                continue  # registered fields are initialized via _regs/_nxt below
            if isinstance(f.datatype, DataTypeRef):
                # Zero-initialize the struct by its fields
                struct_def = ctx.type_m.get(f.datatype.ref_name)
                if struct_def and hasattr(struct_def, 'fields'):
                    for sf in struct_def.fields:
                        lines.append(f"    self->{f.name}.{sf.name} = 0;")
                else:
                    lines.append(f"    /* zero-init {f.name} */")
            elif isinstance(f.datatype, DataTypeArray):
                lines.append(f"    memset(self->{f.name}, 0, sizeof(self->{f.name}));")
            else:
                if f.is_const and comp_cls is not None:
                    default = getattr(comp_cls, f.name, 0)
                    lines.append(f"    self->{f.name} = {default}U;")
                else:
                    lines.append(f"    self->{f.name} = 0;")
        # Registered fields: zero-init both _regs and _nxt with memset,
        # then explicitly set any non-zero fields.
        if ctx.rtl_nxt_fields:
            lines.append(f"    memset(&self->_regs, 0, sizeof(self->_regs));")
            lines.append(f"    memset(&self->_nxt,  0, sizeof(self->_nxt));")
            # Explicitly set registered fields that have non-zero init values (rare).
            field_map = {f.name: f for f in comp.fields}
            for fname in sorted(ctx.rtl_nxt_fields):
                f = field_map[fname]
                if isinstance(f.datatype, DataTypeRef):
                    # Struct fields are zeroed by memset above; no extra work needed.
                    pass
        if ctx.rtl_behav_processes:
            lines.append("    self->_co_pc   = 0;")
            lines.append("    self->_co_tick = 0;")
            lines.append("    self->_co_wake = 0;")
        lines.append("}")
        return lines

    def _src_loc_lines(self, stmt, ctx: SwContext) -> List[str]:
        """Return ``[#line N "file"]`` if debug is on and stmt has a loc."""
        if not ctx.rtl_debug:
            return []
        loc = getattr(stmt, 'loc', None)
        if loc is None or not loc.file or not loc.line:
            return []
        escaped = loc.file.replace('\\', '\\\\').replace('"', '\\"')
        return [f'#line {loc.line} "{escaped}"']

    def _emit_sync_bodies(self, comp, name: str, tm: RtlTypeMapper, ctx: SwContext) -> List[str]:
        """Emit one _sync_<fn>() function per @sync process."""
        wire_names = {wp.name for wp in comp.wire_processes} if hasattr(comp, 'wire_processes') else set()
        const_map = self._build_const_map(comp, ctx)
        all_lines = []
        for fn in comp.sync_processes:
            fn_name = f"{name}_sync_{fn.name.lstrip('_')}"
            all_lines.append(f"static void {fn_name}({name} *self) {{")
            lower = ExprLower(
                comp.fields, ctx.rtl_nxt_fields, indent="    ",
                module_globals=ctx.py_globals,
                wire_names=wire_names,
                comp_name=name,
                const_map=const_map,
            )
            lower._depth = 1
            lower._predecl_locals = True
            # Pre-declare all local variables at function top
            local_names = collect_local_names(fn.body)
            for lname in sorted(local_names):
                all_lines.append(f"    uint32_t {lname} = 0;")
            pad = "    "
            for stmt in fn.body:
                all_lines.extend(self._src_loc_lines(stmt, ctx))
                all_lines.extend(lower._lower_stmt(stmt, True, pad))
            all_lines.append("}")
            all_lines.append("")
        return all_lines

    def _build_const_map(self, comp, ctx: SwContext) -> dict:
        """Return {field_name: int_value} for all is_const fields."""
        comp_cls = ctx.rtl_component_class
        if comp_cls is None:
            return {}
        return {
            f.name: getattr(comp_cls, f.name, 0)
            for f in comp.fields
            if f.is_const
        }

    def _emit_advance(self, comp, name: str, ctx: SwContext) -> List[str]:
        """Emit Foo_advance(): single struct assignment copies _nxt → _regs."""
        lines = [f"void {name}_advance({name} *self) {{"]
        if ctx.rtl_nxt_fields:
            lines.append(f"    self->_regs = self->_nxt;")
        lines.append("}")
        return lines

    def _emit_clock_edge(self, comp, name: str, ctx: SwContext) -> List[str]:
        """Emit Foo_clock_edge(): update wires+comb, then sync processes, then advance."""
        lines = [f"void {name}_clock_edge({name} *self) {{"]
        # Compute wires and combinational outputs before sync processes
        lines.append(f"    {name}_eval_comb(self);")
        # Initialize struct-type nxt shadows from current value so unwritten sub-fields
        # (e.g. bundle inputs) are preserved through advance()
        for fname in sorted(ctx.rtl_nxt_fields):
            for f in comp.fields:
                if f.name == fname and isinstance(f.datatype, DataTypeRef):
                    lines.append(f"    self->_nxt.{fname} = self->_regs.{fname};")
                    break
        # Pipeline stages (inlined C body)
        if ctx.rtl_pipeline_clock_body:
            lines.extend(ctx.rtl_pipeline_clock_body)
        # Sync processes
        for fn in comp.sync_processes:
            fn_name = f"{name}_sync_{fn.name.lstrip('_')}"
            lines.append(f"    {fn_name}(self);")
        lines.append(f"    {name}_advance(self);")
        lines.append("}")
        return lines

    def _emit_run_cycles(self, comp, name: str, ctx: SwContext) -> List[str]:
        """Emit Foo_run_cycles(n): tight C loop — no Python round-trips."""
        lines = [
            f"void {name}_run_cycles({name} *self, uint64_t n) {{",
            f"    for (uint64_t _i = 0; _i < n; _i++) {{",
            f"        {name}_clock_edge(self);",
            f"    }}",
            f"}}",
        ]
        return lines

    def _has_domain_reset(self, comp) -> bool:
        """True if the component uses the domain-based reset API (no explicit reset field)."""
        if not hasattr(comp, "reset_domain") or comp.reset_domain is None:
            return False
        if any(f.name == "reset" for f in comp.fields):
            return False
        return any(f.reset_value is not None for f in comp.fields)

    def _emit_apply_reset(self, comp, name: str, ctx: SwContext) -> List[str]:
        """Emit Foo_apply_reset(): assign reset values to all fields that declare reset=."""
        lines = [f"void {name}_apply_reset({name} *self) {{"]
        for f in comp.fields:
            if f.reset_value is not None:
                if f.name in ctx.rtl_nxt_fields:
                    lines.append(f"    self->_regs.{f.name} = {f.reset_value};")
                    lines.append(f"    self->_nxt.{f.name} = {f.reset_value};")
                else:
                    lines.append(f"    self->{f.name} = {f.reset_value};")
        lines.append("}")
        return lines

    def _emit_eval_comb(self, comp, name: str, tm: RtlTypeMapper, ctx: SwContext) -> List[str]:
        """Emit Foo_eval_comb(): compute wire fields, then call @comb bodies in topological order."""
        wire_names = {wp.name for wp in comp.wire_processes} if hasattr(comp, 'wire_processes') else set()
        const_map = self._build_const_map(comp, ctx)
        lines = [f"void {name}_eval_comb({name} *self) {{"]

        # Compute wire fields (from @property / wire_processes)
        if hasattr(comp, 'wire_processes') and comp.wire_processes:
            for wp in comp.wire_processes:
                lower = ExprLower(
                    comp.fields, ctx.rtl_nxt_fields, indent="    ",
                    module_globals=ctx.py_globals,
                    wire_names=wire_names,
                    comp_name=name,
                    const_map=const_map,
                )
                lower._depth = 1
                # Wire processes have a single return statement; emit as assignment
                ret_stmts = [s for s in wp.body
                             if s.__class__.__name__ == 'StmtReturn' and getattr(s, 'value', None) is not None]
                if ret_stmts:
                    ret_val = lower.lower_expr(ret_stmts[0].value, write_ctx=False)
                    lines.append(f"    self->{wp.name} = {ret_val};")
                else:
                    # Fall back to lowering all non-docstring statements
                    for s in wp.body:
                        if s.__class__.__name__ == 'StmtExpr' and isinstance(getattr(s, 'expr', None), ExprConstant):
                            continue  # skip docstring
                        stmts = lower._lower_stmt(s, False, "    ")
                        lines.extend(stmts)

        # Comb processes (from @zdc.comb)
        for fn in ctx.rtl_comb_order:
            lower = ExprLower(
                comp.fields, ctx.rtl_nxt_fields, indent="    ",
                module_globals=ctx.py_globals,
                wire_names=wire_names,
                comp_name=name,
                const_map=const_map,
            )
            lower._depth = 1
            lower._predecl_locals = True
            # Pre-declare all local variables at function top
            local_names = collect_local_names(fn.body)
            for lname in sorted(local_names):
                lines.append(f"    uint32_t {lname} = 0;")
            pad = "    "
            for stmt in fn.body:
                lines.extend(self._src_loc_lines(stmt, ctx))
                lines.extend(lower._lower_stmt(stmt, False, pad))
        lines.append("}")
        return lines

    # ------------------------------------------------------------------
    # ctypes wrapper
    # ------------------------------------------------------------------

    def _emit_ctypes(self, comp, name: str, tm: RtlTypeMapper, ctx: SwContext) -> str:
        lines = [
            "import ctypes",
            "import os as _os",
            "",
        ]

        # Emit embedded ctypes structures for DataTypeRef fields
        seen_structs = set()
        for f in comp.fields:
            if not isinstance(f.datatype, DataTypeRef):
                continue
            ref_name = f.datatype.ref_name
            if ref_name in seen_structs:
                continue
            seen_structs.add(ref_name)
            struct_def = ctx.type_m.get(ref_name)
            if struct_def is None or not hasattr(struct_def, 'fields'):
                continue
            lines.append(f"class {ref_name}(ctypes.Structure):")
            lines.append(f"    _fields_ = [")
            for sf in struct_def.fields:
                if isinstance(sf.datatype, DataTypeInt):
                    c_type = tm.map_rtl_int_type(sf.datatype)
                    ct = _CTYPES_INT_MAP.get(c_type, "ctypes.c_uint32")
                    lines.append(f'        ("{sf.name}", {ct}),')
            lines.append("    ]")
            lines.append("")

        # Registered fields: emit a _Regs sub-structure before State class
        if ctx.rtl_nxt_fields:
            lines.append(f"class _{name}_Regs(ctypes.Structure):")
            lines.append(f"    _fields_ = [")
            for f in self._sorted_regs_fields(comp, tm, ctx):
                if isinstance(f.datatype, DataTypeInt):
                    c_type = tm.map_rtl_int_type(f.datatype)
                    ct = _CTYPES_INT_MAP.get(c_type, "ctypes.c_uint32")
                    lines.append(f'        ("{f.name}", {ct}),')
                elif isinstance(f.datatype, DataTypeRef):
                    ref_name = f.datatype.ref_name
                    lines.append(f'        ("{f.name}", {ref_name}),')
            lines.append("    ]")
            lines.append("")

        lines += [
            f"class State(ctypes.Structure):",
            f"    _fields_ = [",
        ]

        # Non-registered fields (those NOT in nxt_fields) — in comp.fields order
        for f in comp.fields:
            if f.name in ctx.rtl_nxt_fields:
                continue  # emitted via _regs/_nxt sub-struct below
            if isinstance(f.datatype, DataTypeInt):
                c_type = tm.map_rtl_int_type(f.datatype)
                ct = _CTYPES_INT_MAP.get(c_type, "ctypes.c_uint32")
                lines.append(f'        ("{f.name}", {ct}),')
            elif isinstance(f.datatype, DataTypeRef):
                ref_name = f.datatype.ref_name
                lines.append(f'        ("{f.name}", {ref_name}),')
            elif isinstance(f.datatype, DataTypeArray):
                elem = f.datatype.element_type
                if isinstance(elem, DataTypeInt):
                    c_type = tm.map_rtl_int_type(elem)
                    ct = _CTYPES_INT_MAP.get(c_type, "ctypes.c_uint32")
                else:
                    ct = "ctypes.c_uint32"
                lines.append(f'        ("{f.name}", {ct} * {f.datatype.size}),')

        # Wire fields (from @property / wire_processes) — must match C struct layout
        if hasattr(comp, 'wire_processes') and comp.wire_processes:
            for wp in comp.wire_processes:
                ret = getattr(wp, 'returns', None)
                if ret is not None and isinstance(ret, DataTypeInt):
                    c_type = tm.map_rtl_int_type(ret)
                else:
                    c_type = "uint32_t"
                ct = _CTYPES_INT_MAP.get(c_type, "ctypes.c_uint32")
                lines.append(f'        ("{wp.name}", {ct}),')

        # Embed _regs and _nxt sub-struct instances
        if ctx.rtl_nxt_fields:
            lines.append(f'        ("_regs", _{name}_Regs),')
            lines.append(f'        ("_nxt",  _{name}_Regs),')

        # Behavioral coroutine ctypes fields (come last in the C struct)
        if ctx.rtl_behav_processes:
            lines += [
                '        ("_co_pc",   ctypes.c_int32),',
                '        ("_co_tick", ctypes.c_uint64),',
                '        ("_co_wake", ctypes.c_uint64),',
            ]
            if ctx.rtl_debug:
                # Debug fields: _co_src_file (ptr), _co_src_line (int32),
                # _co_name (ptr), _co_frame (opaque pointer-sized).
                # ZspCoroFrame_t holds {name, loc.file, loc.line, *prev} so
                # its size is 3 pointers + 1 int32 — model as raw bytes.
                import ctypes as _ct
                _ptr_sz = _ct.sizeof(_ct.c_void_p)
                _frame_sz = 3 * _ptr_sz + 4  # co_name + loc.file + *prev + loc.line
                lines += [
                    '        ("_co_src_file", ctypes.c_char_p),',
                    '        ("_co_src_line", ctypes.c_int32),',
                    '        ("_co_name",     ctypes.c_char_p),',
                    f'        ("_co_frame",   ctypes.c_uint8 * {_frame_sz}),',
                ]

        lines += [
            "    ]",
            "",
        ]

        # Generate @property wrappers on State for all registered fields.
        # This preserves backwards-compatible access (state.field) while
        # the underlying C struct stores them in the nested _regs/_nxt sub-structs.
        if ctx.rtl_nxt_fields:
            for fname in sorted(ctx.rtl_nxt_fields):
                lines += [
                    f"    @property",
                    f"    def {fname}(self): return self._regs.{fname}",
                    f"    @{fname}.setter",
                    f"    def {fname}(self, v): self._regs.{fname} = v",
                    "",
                ]
            # Also expose _nxt fields for direct inspection (read-only alias)
            for fname in sorted(ctx.rtl_nxt_fields):
                lines += [
                    f"    @property",
                    f"    def {fname}_nxt(self): return self._nxt.{fname}",
                    f"    @{fname}_nxt.setter",
                    f"    def {fname}_nxt(self, v): self._nxt.{fname} = v",
                    "",
                ]
        # Behavioral sim_run wrapper
        if ctx.rtl_behav_processes:
            lines += [
                "def sim_run(state, n_cycles, lib=None, period_ps=None):",
                "    \"\"\"Run n_cycles of simulation (RTL + behavioral).\"\"\"",
                "    if lib is None:",
                "        raise ValueError('lib must be provided')",
                f"    lib.{name}_sim_run.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]",
                f"    lib.{name}_sim_run.restype = None",
                f"    lib.{name}_sim_run(ctypes.byref(state), n_cycles)",
                "",
            ]

        # run_cycles bulk helper (always present)
        lines += [
            f"def run_cycles(state, n, lib):",
            f"    \"\"\"Run n clock cycles in a tight C loop (no Python overhead per cycle).\"\"\"",
            f"    lib.{name}_run_cycles.argtypes = [ctypes.POINTER(State), ctypes.c_uint64]",
            f"    lib.{name}_run_cycles.restype = None",
            f"    lib.{name}_run_cycles(ctypes.byref(state), n)",
            "",
        ]

        # apply_reset helper for domain-based reset components
        if self._has_domain_reset(comp):
            lines += [
                f"def apply_reset(state, lib):",
                f"    \"\"\"Apply reset values to all fields declared with reset= in the domain API.\"\"\"",
                f"    lib.{name}_apply_reset.argtypes = [ctypes.POINTER(State)]",
                f"    lib.{name}_apply_reset.restype = None",
                f"    lib.{name}_apply_reset(ctypes.byref(state))",
                "",
            ]

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Behavioral coroutine emission
    # ------------------------------------------------------------------

    def _emit_co_run(self, comp, name: str, ctx: SwContext) -> List[str]:
        """Emit Foo_co_run(self, tick): switch(pc) coroutine state machine."""
        if not ctx.rtl_behav_processes:
            return []
        proc = ctx.rtl_behav_processes[0]  # Emit first process only for now.
        proc_name = getattr(proc, 'name', '_co')
        lines = [
            f"void {name}_co_run({name} *self, zsp_ps_t tick) {{",
        ]
        # B4: push coroutine frame onto thread-local stack at entry
        if ctx.rtl_debug:
            lines += [
                f'    zsp_push_frame(&self->_co_frame, "{proc_name}", self->_co_src_file, self->_co_src_line);',
            ]
        lines += [
            "    switch(self->_co_pc) {",
            "    case 0:;",  # initial entry point
        ]
        state_counter = [0]  # mutable counter via list
        self._emit_co_stmts(proc.body, comp, name, ctx, lines, state_counter)
        lines += [
            "    }",
        ]
        # B4: pop coroutine frame on exit
        if ctx.rtl_debug:
            lines.append("    zsp_pop_frame();")
        lines.append("}")
        return lines

    def _emit_co_stmts(self, stmts, comp, name, ctx, lines, state_counter, loop_label=None):
        """Recursively emit IR statements as coroutine C code."""
        for stmt in stmts:
            if isinstance(stmt, StmtWhile):
                # Emit: L_loop_N: at the top of the while body
                lbl = f"L_loop_{state_counter[0]}"
                lines.append(f"    {lbl}:")
                # Recurse into while body, passing lbl for goto at end
                self._emit_co_stmts(
                    stmt.body, comp, name, ctx, lines, state_counter, loop_label=lbl
                )
                # If we exit the while (test not True forever): fall through
                # For `while True:` loops, the goto at end of body handles looping.
                continue

            if isinstance(stmt, StmtExpr) and isinstance(stmt.expr, ExprAwait):
                call = stmt.expr.value
                if isinstance(call, ExprCall):
                    susp = WaitLowerPass.lower_await(
                        call, comp.fields, ctx.rtl_domain_period_ps, ctx.rtl_warnings
                    )
                    state_counter[0] += 1
                    resume_state = state_counter[0]
                    lines.extend(self._src_loc_lines(stmt, ctx))
                    loc = getattr(stmt, 'loc', None)
                    # B3: store Python source location in coroutine struct at each suspension
                    if ctx.rtl_debug:
                        if loc and loc.file and loc.line:
                            esc = loc.file.replace('\\', '\\\\').replace('"', '\\"')
                            lines.append(f'        self->_co_src_file = "{esc}";')
                            lines.append(f"        self->_co_src_line = {loc.line};")
                    # C4: accumulate suspension point metadata for source map
                    if ctx.rtl_debug:
                        ctx.rtl_suspension_points.append({
                            "state":    resume_state,
                            "src_file": loc.file if loc and loc.file else None,
                            "src_line": loc.line if loc and loc.line else 0,
                            "src_col":  loc.pos  if loc and loc.pos  else 0,
                            "kind":     "wait_yield" if susp.is_yield else "wait_cycles",
                            "delta_ps": 0 if susp.is_yield else (
                                int(susp.tick_delta_expr)
                                if isinstance(susp.tick_delta_expr, int)
                                else str(susp.tick_delta_expr)
                            ),
                        })
                    if susp.is_yield:
                        # wait_cycles(0): yield at same tick
                        lines.append(f"        self->_co_wake = tick;")
                    else:
                        lines.append(f"        self->_co_wake = tick + {susp.tick_delta_expr};")
                    lines.append(f"        self->_co_pc = {resume_state};")
                    lines.append(f"        return;")
                    lines.append(f"    case {resume_state}:;")
                continue

            # Ordinary statement: emit via simplified lowering
            lines.extend(self._src_loc_lines(stmt, ctx))
            c_stmts = self._lower_behav_stmt(stmt, comp, ctx)
            for s in c_stmts:
                lines.append(f"        {s}")

        # End of while loop body: jump back to the loop label
        if loop_label is not None:
            lines.append(f"        goto {loop_label};")

    def _lower_behav_stmt(self, stmt, comp, ctx) -> List[str]:
        """Lower a non-await IR statement to C for the behavioral coroutine."""
        fields = comp.fields
        if isinstance(stmt, StmtAugAssign):
            target_c = self._behav_lower_expr(stmt.target, fields)
            value_c  = self._behav_lower_expr(stmt.value, fields)
            op_map = {
                AugOp.Add:  "+=",
                AugOp.Sub:  "-=",
                AugOp.Mult: "*=",
                AugOp.BitAnd: "&=",
                AugOp.BitOr:  "|=",
                AugOp.BitXor: "^=",
            }
            op = op_map.get(stmt.op, "+=")
            return [f"{target_c} {op} {value_c};"]
        if isinstance(stmt, StmtAssign):
            target_c = self._behav_lower_expr(stmt.target, fields)
            value_c  = self._behav_lower_expr(stmt.value, fields)
            return [f"{target_c} = {value_c};"]
        if isinstance(stmt, StmtExpr):
            # Bare expression statement (e.g. function call)
            e_c = self._behav_lower_expr(stmt.expr, fields)
            return [f"{e_c};"]
        return [f"/* unhandled stmt {type(stmt).__name__} */"]

    def _behav_lower_expr(self, expr, fields) -> str:
        """Minimal expression lowerer for behavioral coroutine bodies."""
        if isinstance(expr, ExprConstant):
            return str(expr.value)
        if isinstance(expr, ExprRefField):
            if expr.index < len(fields):
                return f"self->{fields[expr.index].name}"
            return f"self->_f{expr.index}"
        if isinstance(expr, ExprAttribute):
            base_c = self._behav_lower_expr(expr.value, fields)
            return f"{base_c}.{expr.attr}"
        if isinstance(expr, ExprCall):
            # int(x) → just emit the inner expression
            func = expr.func
            fname = func.attr if isinstance(func, ExprAttribute) else (
                func.name if isinstance(func, ExprRefUnresolved) else "fn"
            )
            if fname == "int" and expr.args:
                return self._behav_lower_expr(expr.args[0], fields)
            args_c = ", ".join(self._behav_lower_expr(a, fields) for a in expr.args)
            return f"{fname}({args_c})"
        return f"/* expr {type(expr).__name__} */"

    def _emit_sim_run(self, comp, name: str, ctx: SwContext) -> List[str]:
        """Emit Foo_sim_run(self, n_cycles): RTL clock loop + coroutine wake.

        The coroutine is primed once (before any clock edges) on first call,
        so that ``wait_cycles(D)`` fires every D clock edges and
        count = floor(n_total_cycles / D) after n_total_cycles.
        """
        period = ctx.rtl_domain_period_ps
        lines = [
            f"void {name}_sim_run({name} *self, uint64_t n_cycles) {{",
            f"    /* Prime the coroutine on first call (before any clock edges). */",
            f"    if (self->_co_pc == 0) {{",
            f"        {name}_co_run(self, self->_co_tick);",
            f"    }}",
            f"    for (uint64_t c = 0; c < n_cycles; c++) {{",
            f"        {name}_clock_edge(self);",
            f"        {name}_eval_comb(self);",
            f"        self->_co_tick += {period}ULL;",
            f"        if (self->_co_pc >= 0 && self->_co_tick >= self->_co_wake) {{",
            f"            {name}_co_run(self, self->_co_tick);",
            f"        }}",
            f"    }}",
            "}",
        ]
        return lines

    # ------------------------------------------------------------------
    # C1: Source-map builder
    # ------------------------------------------------------------------

    def _build_srcmap(self, comp, name: str, ctx: SwContext) -> str:
        """Build a JSON source map for ``comp``.

        Schema (version 1) matches §7.2 of ``zuspec_c_debug_design.md``.
        """
        tm = RtlTypeMapper()

        def _field_kind(f) -> str:
            from zuspec.ir.core.fields import SignalDirection, FieldKind
            if f.direction == SignalDirection.INPUT:
                return "input"
            if f.direction == SignalDirection.OUTPUT:
                return "output"
            if f.kind == FieldKind.Field:
                return "register"
            return "field"

        fields_out = []
        for f in comp.fields:
            if f.is_const:
                continue
            if isinstance(f.datatype, DataTypeInt):
                width  = f.datatype.bits if f.datatype.bits > 0 else 64
                signed = f.datatype.signed
            else:
                width  = 32
                signed = False
            fields_out.append({
                "src_name": f.name,
                "c_name":   f.name,
                "width":    width,
                "signed":   signed,
                "kind":     _field_kind(f),
            })

        # nxt_fields: names of fields that have a _nxt shadow (registered)
        nxt_fields = sorted(ctx.rtl_nxt_fields)

        # coro_fields: coroutine internal fields always present in debug builds
        coro_fields = [
            "_co_pc", "_co_wake", "_co_tick",
            "_co_src_file", "_co_src_line", "_co_name", "_co_frame",
        ]

        # processes: sync and wire
        processes = []
        for fn in comp.sync_processes:
            processes.append({"kind": "sync", "name": fn.name})
        if hasattr(comp, 'wire_processes'):
            for wp in comp.wire_processes:
                processes.append({"kind": "wire", "name": wp.name})
        for fn in ctx.rtl_comb_order:
            processes.append({"kind": "comb", "name": fn.name})

        # coroutines with their suspension points
        coroutines = []
        for bp in ctx.rtl_behav_processes:
            # bp may be a Function IR node
            bp_name = getattr(bp, 'name', str(bp))
            # filter suspension_points that belong to this coroutine
            # (all are in one coroutine for now; partitioning by name TBD)
            suspensions = [
                {
                    "state":    sp["state"],
                    "src_file": sp["src_file"],
                    "src_line": sp["src_line"],
                    "src_col":  sp["src_col"],
                    "kind":     sp["kind"],
                    "delta_ps": sp["delta_ps"],
                }
                for sp in ctx.rtl_suspension_points
            ]
            coroutines.append({
                "src_name":          bp_name,
                "suspension_points": suspensions,
            })

        sm = {
            "version":    1,
            "component":  name,
            "c_type":     name,
            "fields":     fields_out,
            "nxt_fields": nxt_fields,
            "coro_fields": coro_fields,
            "processes":  processes,
            "coroutines": coroutines,
        }
        return json.dumps(sm, indent=2)

    # ------------------------------------------------------------------
    # C2a: Emit _srcmap.c  — JSON payload in ELF .zuspec_srcmap section
    # ------------------------------------------------------------------

    def _emit_srcmap_c(self, name: str, json_str: str) -> str:
        """Return C source embedding ``json_str`` in ``.zuspec_srcmap``."""
        # Escape for embedding as a single C string literal (no line splitting)
        escaped = (
            json_str
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )
        lines = [
            f'/* Auto-generated source map for {name} — DO NOT EDIT */',
            f'#ifdef ZS_DEBUG',
            f'__attribute__((section(".zuspec_srcmap"), used))',
            f'static const char _zuspec_srcmap_{name}[] = "{escaped}";',
            f'#endif /* ZS_DEBUG */',
        ]
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # C2b: Emit _debug.c  — GDB script embedded in .debug_gdb_scripts
    # ------------------------------------------------------------------

    def _emit_debug_c(self, name: str) -> str:
        """Return C source embedding the GDB auto-load script in the ELF."""
        # Read zuspec_gdb.py relative to this file
        gdb_script_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "debug", "zuspec_gdb.py"
        )
        try:
            with open(gdb_script_path, "r", encoding="utf-8") as fh:
                script_content = fh.read()
        except OSError:
            script_content = "# zuspec_gdb.py not found\n"

        # ELF .debug_gdb_scripts inline Python format:
        # \x04 + "script-name\0" + script-text + "\0"
        # We encode as a C string with escaped bytes.
        header = "\\x04zuspec_gdb\\0"
        escaped_script = (
            script_content
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n\"\n    \"")
        )
        lines = [
            f'/* Auto-generated GDB auto-load script section for {name} */',
            f'#ifdef ZS_DEBUG',
            f'__attribute__((section(".debug_gdb_scripts"), used))',
            f'static const char _zuspec_gdb_script_{name}[] =',
            f'    "{header}"',
            f'    "{escaped_script}\\0";',
            f'#endif /* ZS_DEBUG */',
        ]
        return "\n".join(lines) + "\n"


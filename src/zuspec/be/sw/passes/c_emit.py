"""CEmitPass — emit `.h` / `.c` files from SW IR nodes in SwContext.

Pure translation of SW IR to text; no semantic decisions are made here.

Emit structure per component:
  _emit_header(comp_name, ctxt)          → <comp_name>.h
  _emit_source(comp_name, ctxt)          → <comp_name>.c
    _emit_struct_def(SwCompInst)
    _emit_init_fn(SwCompInst)
    _emit_connect_fn(SwExportBind nodes)
    _emit_scheduler(SwSchedulerNode)
      _emit_seq_block(SwSeqBlock)
      _emit_par_block(SwParBlock)
      _emit_select_node(SwSelectNode)
      _emit_action_exec(SwActionExec)
    _emit_sync_function(Function)
    _emit_coroutine(SwCoroutineFrame)
      _emit_continuation(SwContinuation)
      _emit_suspend_point(SwSuspendPoint)
    _emit_fifo_decl(SwFifo)
    _emit_func_ptr_struct(SwFuncPtrStruct)
    _emit_mutex_acquire(SwMutexAcquire)
    _emit_mutex_release(SwMutexRelease)
    _emit_indexed_select(SwIndexedSelect)
"""
from __future__ import annotations

import dataclasses as _dc
import io
import typing as _typing
from typing import Any, Dict, List, Optional, Set, Tuple

from zuspec.dataclasses import ir
try:
    from zuspec.dataclasses.types import IndexedRegFile as _IndexedRegFile
    from zuspec.dataclasses.types import IndexedPool as _IndexedPool
    from zuspec.dataclasses.types import ClaimPool as _ClaimPool
except ImportError:
    _IndexedRegFile = None  # type: ignore
    _IndexedPool = None  # type: ignore
    _ClaimPool = None  # type: ignore
from zuspec.be.sw.ir.activity import (
    SwSchedulerNode,
    SwActionExec,
    SwSeqBlock,
    SwParBlock,
    SwSelectNode,
)
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.channel import (
    SwExportBind,
    SwFifo,
    SwFifoPop,
    SwFifoPush,
    SwFuncPtrStruct,
    SwFuncSlot,
)
from zuspec.be.sw.ir.coroutine import (
    SwContinuation,
    SwCoroutineFrame,
    SwLocalVar,
    SwSuspendCall,
    SwSuspendFifoPop,
    SwSuspendFifoPush,
    SwSuspendMutex,
    SwSuspendPoint,
    SwSuspendWait,
)
from zuspec.be.sw.ir.memory import SwMemRead, SwMemWrite, SwRegRead, SwRegWrite
from zuspec.be.sw.ir.resource import SwIndexedSelect, SwMutexAcquire, SwMutexRelease
from zuspec.be.sw.passes.elaborate import SwCompInst
from zuspec.be.sw.pipeline import SwPass
from zuspec.be.sw.stmt_generator import StmtGenerator
from zuspec.be.sw.type_mapper import TypeMapper


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _round_to_std_bits(bits: int) -> int:
    """Round *bits* up to the nearest standard C integer width (8/16/32/64)."""
    if bits <= 8:
        return 8
    if bits <= 16:
        return 16
    if bits <= 32:
        return 32
    return 64


def _collect_unresolved_names(stmts: list) -> Set[str]:
    """Collect ExprRefUnresolved names from *stmts* that are used as variables.

    Names that appear only as the ``func`` argument of a call (i.e. as
    free-function callees) or only as the ``value`` base of an attribute
    access (e.g. ``AluOp.ADD``) are **excluded** because they should not be
    declared as local variables.  Known Python builtins and module names
    that have C-side equivalents (int, bool, zdc, range, print, …) are also
    excluded.
    """
    _BUILTIN_NAMES = frozenset({
        "int", "bool", "float", "str", "len", "range", "print",
        "zdc", "_s32", "_sdiv32_trunc",
    })
    names: Set[str] = set()
    callee_names: Set[str] = set()
    attr_base_names: Set[str] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, ir.ExprRefUnresolved):
            names.add(node.name)
        # ExprRefLocal: explicitly-typed local variable (e.g. "shamt: zdc.u32 = ...")
        if isinstance(node, ir.ExprRefLocal):
            names.add(node.name)
        # Track names used as direct callees so we can exclude them later
        if isinstance(node, ir.ExprCall):
            if isinstance(node.func, ir.ExprRefUnresolved):
                callee_names.add(node.func.name)
        # Track names used only as attribute bases (e.g. AluOp in AluOp.ADD)
        if isinstance(node, ir.ExprAttribute):
            if isinstance(node.value, ir.ExprRefUnresolved):
                attr_base_names.add(node.value.name)
        # Recurse into children
        for attr in ("lhs", "rhs", "left", "value", "operand", "func",
                     "base", "test", "target", "targets",
                     "subject",      # StmtMatch
                     "pattern",      # StmtMatchCase / PatternAs
                     "guard",        # StmtMatchCase
                     ):
            child = getattr(node, attr, None)
            if child is not None:
                if isinstance(child, list):
                    for c in child:
                        _visit(c)
                else:
                    _visit(child)
        for attr in ("args", "body", "orelse", "comparators", "values",
                     "cases",        # StmtMatch
                     ):
            children = getattr(node, attr, None)
            if isinstance(children, list):
                for c in children:
                    _visit(c)

    for stmt in stmts:
        _visit(stmt)

    # Also collect assignment targets (StmtAssign lhs may be ExprRefUnresolved or ExprRefLocal)
    def _collect_assign_targets(stmts_inner: list) -> None:
        for stmt in stmts_inner:
            if isinstance(stmt, ir.StmtAssign):
                for target in (stmt.targets or []):
                    if isinstance(target, (ir.ExprRefUnresolved, ir.ExprRefLocal)):
                        names.add(target.name)
            for attr in ("body", "orelse"):
                children = getattr(stmt, attr, None)
                if isinstance(children, list):
                    _collect_assign_targets(children)
            # StmtMatch cases
            if hasattr(stmt, "cases"):
                for case in stmt.cases:
                    _collect_assign_targets(case.body)

    _collect_assign_targets(stmts)
    # Exclude callees, attribute-base-only names, and known Python builtins
    # Names that appear BOTH as standalone vars AND as attr bases are kept.
    pure_attr_bases = attr_base_names - (names - attr_base_names)
    return (names - callee_names - pure_attr_bases) - _BUILTIN_NAMES


def _collect_stub_ptr_names(stmts: list) -> Set[str]:
    """Return names of ExprRefUnresolved nodes that appear as the value of ExprAttribute.

    These names are used via '->field' pointer dereference (e.g. 'claim->t->execute').
    They need to be declared as '_zsp_stub_t *' rather than plain 'uint32_t'.
    """
    names: Set[str] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, ir.ExprAttribute):
            if isinstance(node.value, ir.ExprRefUnresolved):
                names.add(node.value.name)
        for attr in ("lhs", "rhs", "left", "value", "operand", "func",
                     "base", "test", "target", "targets", "subject"):
            child = getattr(node, attr, None)
            if child is not None:
                if isinstance(child, list):
                    for c in child:
                        _visit(c)
                else:
                    _visit(child)
        for attr in ("args", "body", "orelse", "comparators", "values", "cases"):
            children = getattr(node, attr, None)
            if isinstance(children, list):
                for c in children:
                    _visit(c)

    for stmt in stmts:
        _visit(stmt)
    return names


def _collect_action_type_hints(stmts: list) -> Dict[str, "ir.DataTypeAction"]:
    """Return {var_name: DataTypeAction} for every StmtAnnAssign with an action ir_type."""
    hints: Dict[str, Any] = {}
    for stmt in stmts:
        if isinstance(stmt, ir.StmtAnnAssign):
            ir_type = getattr(stmt, "ir_type", None)
            if isinstance(ir_type, ir.DataTypeAction):
                tgt = getattr(stmt, "target", None)
                if isinstance(tgt, ir.ExprRefLocal):
                    hints[tgt.name] = ir_type
        for attr in ("body", "orelse"):
            children = getattr(stmt, attr, None)
            if isinstance(children, list):
                hints.update(_collect_action_type_hints(children))
    return hints


def _c_type(dtype: Optional[ir.DataType], ctxt: SwContext) -> str:
    """Map a DataType to a C type string."""
    if dtype is None:
        return "void"
    if isinstance(dtype, ir.DataTypeInt):
        if dtype.bits < 0:
            return "int32_t"
        # Round up to the next standard C integer width
        bits = dtype.bits
        if bits <= 8:
            width = 8
        elif bits <= 16:
            width = 16
        elif bits <= 32:
            width = 32
        else:
            width = 64
        if dtype.signed:
            return f"int{width}_t"
        return f"uint{width}_t"
    if isinstance(dtype, ir.DataTypeRef):
        if dtype.ref_name == "bool":
            return "uint8_t"
        resolved = ctxt.type_m.get(dtype.ref_name)
        if resolved:
            return _c_type(resolved, ctxt)
        return dtype.ref_name
    if isinstance(dtype, ir.DataTypeComponent):
        return dtype.name or "comp_t"
    if isinstance(dtype, ir.DataTypeEnum):
        return "uint32_t"
    if isinstance(dtype, ir.DataTypeAction):
        return f"{dtype.name}_t"
    if isinstance(dtype, ir.DataTypeChannel):
        elem = _c_type(dtype.element_type, ctxt)
        return f"zsp_fifo_t /* {elem} */"
    return "void"


def _py_uint_width(annotated_type: Any) -> int:
    """Extract bit width from a zdc Annotated integer type (e.g. u5 -> 5, u32 -> 32)."""
    args = _typing.get_args(annotated_type)
    if len(args) >= 2:
        meta = args[1]
        if hasattr(meta, "width"):
            return meta.width
    return 32


class _FieldMeta:
    """Extracted metadata for a single component field."""

    __slots__ = (
        "name", "kind", "c_type", "depth", "elem_bits", "idx_bits",
        "accessible", "callable_ret_bits", "callable_arg_bits",
        "mem_size", "comp_type", "py_struct_cls",
    )

    def __init__(self):
        self.name: str = ""
        self.kind: str = "plain"  # plain | indexed_regfile | indexed_pool | callable_port | memory | component | py_struct | skip
        self.c_type: str = "int32_t"
        self.depth: int = 0
        self.elem_bits: int = 32
        self.idx_bits: int = 5
        self.mem_size: int = 0   # for kind=="memory": number of elements
        self.comp_type: str = ""  # for kind=="component": C type name of sub-component
        self.accessible: bool = False  # True when a C getter/setter will be generated
        self.callable_ret_bits: int = 32
        self.callable_arg_bits: List[int] = []
        self.py_struct_cls = None  # for kind=="py_struct": the Python dataclasses.dataclass


def _collect_field_meta(
    dtype: ir.DataTypeComponent, ctxt: SwContext
) -> Dict[str, _FieldMeta]:
    """Build a mapping from field name to _FieldMeta for *dtype*.

    Uses both the IR field list and Python class annotations (via
    ``dtype.py_type``) to fill in generic type parameters for
    ``IndexedRegFile``, ``IndexedPool``, and callable ports.
    """
    py_hints: Dict[str, Any] = {}
    py_field_meta: Dict[str, Any] = {}
    if dtype.py_type is not None:
        try:
            py_hints = _typing.get_type_hints(dtype.py_type, include_extras=True)
        except Exception:
            pass
        try:
            py_field_meta = {f.name: f.metadata for f in _dc.fields(dtype.py_type)}
        except Exception:
            pass

    result: Dict[str, _FieldMeta] = {}
    for field in dtype.fields:
        m = _FieldMeta()
        m.name = field.name

        if field.kind == ir.FieldKind.CallablePort:
            m.kind = "callable_port"
            # Recover arg/return types from Python hint if available
            hint = py_hints.get(field.name)
            if hint is not None:
                call_args = _typing.get_args(hint)  # ([arg_types], ReturnType)
                if call_args:
                    arg_list = call_args[0] if isinstance(call_args[0], list) else []
                    ret_type = call_args[1] if len(call_args) > 1 else None
                    m.callable_arg_bits = [_py_uint_width(a) for a in arg_list]
                    if ret_type is not None:
                        # Awaitable[T] → unwrap
                        inner = _typing.get_args(ret_type)
                        m.callable_ret_bits = _py_uint_width(inner[0]) if inner else 32
            m.accessible = False
            result[field.name] = m
            continue

        if isinstance(field.datatype, ir.DataTypeRef):
            ref = field.datatype.ref_name
            if ref == "IndexedRegFile":
                m.kind = "indexed_regfile"
                hint = py_hints.get(field.name)
                if hint is not None:
                    args = _typing.get_args(hint)
                    if len(args) >= 2:
                        m.idx_bits = _py_uint_width(args[0])
                        m.elem_bits = _py_uint_width(args[1])
                        m.depth = 2 ** m.idx_bits
                else:
                    m.depth = 32
                    m.elem_bits = 32
                    m.idx_bits = 5
                m.c_type = f"uint{_round_to_std_bits(m.elem_bits)}_t"
                m.accessible = False
                result[field.name] = m
                continue

            if ref == "IndexedPool":
                m.kind = "indexed_pool"
                fmd = py_field_meta.get(field.name, {})
                m.depth = fmd.get("depth", 32)
                hint = py_hints.get(field.name)
                if hint is not None:
                    args = _typing.get_args(hint)
                    if args:
                        m.idx_bits = _py_uint_width(args[0])
                m.accessible = False
                result[field.name] = m
                continue

        if isinstance(field.datatype, ir.DataTypeMemory):
            m.kind = "memory"
            m.mem_size = field.datatype.size or 1024
            # Derive element width from element_type
            et = field.datatype.element_type
            if isinstance(et, ir.DataTypeInt):
                m.elem_bits = et.bits if et.bits > 0 else 32
            else:
                # Fall back to Python type hint: Memory[zdc.uint8_t] etc.
                hint = py_hints.get(field.name)
                if hint is not None:
                    args = _typing.get_args(hint)
                    if args:
                        m.elem_bits = _py_uint_width(args[0])
                    else:
                        m.elem_bits = 32
                else:
                    m.elem_bits = 32
            m.c_type = f"uint{_round_to_std_bits(m.elem_bits)}_t"
            m.accessible = True
            result[field.name] = m
            continue

        if isinstance(field.datatype, ir.DataTypeInt):
            if field.datatype.bits < 0:
                m.kind = "skip"
                m.accessible = False
            else:
                m.kind = "plain"
                m.c_type = _c_type(field.datatype, ctxt)
                m.accessible = True
        elif isinstance(field.datatype, ir.DataTypeRef) and field.datatype.ref_name == "bool":
            m.kind = "plain"
            m.c_type = "uint8_t"
            m.accessible = True
        else:
            # Check if this is a sub-component field (DataTypeRef → DataTypeComponent)
            resolved_dt = None
            if isinstance(field.datatype, ir.DataTypeRef):
                resolved_dt = ctxt.type_m.get(field.datatype.ref_name)
            if isinstance(resolved_dt, ir.DataTypeComponent) and field.kind == ir.FieldKind.Field:
                m.kind = "component"
                m.comp_type = resolved_dt.name or field.datatype.ref_name
                m.accessible = False
            else:
                # Check if the Python type hint is a plain dataclasses.dataclass
                py_cls = py_hints.get(field.name)
                if py_cls is not None and _dc.is_dataclass(py_cls) and isinstance(py_cls, type):
                    m.kind = "py_struct"
                    m.comp_type = py_cls.__name__
                    m.py_struct_cls = py_cls
                    m.accessible = False
                else:
                    c = _c_type(field.datatype, ctxt)
                    # Only expose if it resolved to a concrete C integer type
                    if c.startswith("uint") or c.startswith("int"):
                        m.kind = "plain"
                        m.c_type = c
                        m.accessible = True
                    else:
                        m.kind = "skip"
                        m.accessible = False

        result[field.name] = m
    return result


def _py_type_to_c(py_type) -> str:
    """Map a Python type annotation to a C type string for Python dataclass fields."""
    if py_type is int:
        return "int32_t"
    if py_type is bool:
        return "uint8_t"
    if py_type is float:
        return "double"
    # Handle string annotations like 'int', 'bool'
    if isinstance(py_type, str):
        if py_type == "int":
            return "int32_t"
        if py_type == "bool":
            return "uint8_t"
        if py_type == "float":
            return "double"
    return "int32_t"  # safe default


def _emit_py_struct_typedef(py_cls: type, w) -> None:
    """Emit a C typedef struct for a plain Python dataclasses.dataclass."""
    name = py_cls.__name__
    w.line(f"typedef struct {{")
    w.indent()
    for f in _dc.fields(py_cls):
        c_t = _py_type_to_c(f.type)
        w.line(f"{c_t} {f.name};")
    w.dedent()
    w.line(f"}} {name}_t;")
    w.line("")


def _resolve_datatype(dtype: ir.DataType, ctxt: SwContext) -> ir.DataType:
    """Resolve a DataTypeRef through the context type map."""
    if isinstance(dtype, ir.DataTypeRef):
        resolved = ctxt.type_m.get(dtype.ref_name)
        if resolved is not None:
            return resolved
    return dtype


def _decode_bind_wirings(
    dtype: ir.DataTypeComponent,
    ctxt: SwContext,
) -> List[Tuple[str, str, str, str, str, str]]:
    """Decode ``dtype.bind_map`` into (lhs_subcomp, lhs_port, lhs_type,
    rhs_subcomp, rhs_type, c_wire_fn) tuples for use in the init function.

    Only two-level LHS references (``self.subcomp.port``) are handled.
    RHS may be:
      - One-level  (``self.mem``)   → finds the first Memory field in the RHS
        component and uses ``{rhs_type}_mem_fetch_{mem_field}`` as the wire fn.
      - Two-level  (``self.mem.icache_out``) → uses ``{rhs_type}_{export_name}``.
    """
    results: List[Tuple[str, str, str, str, str, str]] = []

    from zuspec.dataclasses.ir.expr import TypeExprRefSelf, ExprRefField as _ExprRefField

    for bind in getattr(dtype, "bind_map", []):
        lhs = bind.lhs
        rhs = bind.rhs

        # LHS must be 2-level: ExprRefField(ExprRefField(Self, i0), i1)
        if not (
            isinstance(lhs, _ExprRefField)
            and isinstance(lhs.base, _ExprRefField)
            and isinstance(lhs.base.base, TypeExprRefSelf)
        ):
            continue

        lhs_subcomp_idx = lhs.base.index
        lhs_port_idx = lhs.index
        if lhs_subcomp_idx >= len(dtype.fields):
            continue

        lhs_subcomp_name = dtype.fields[lhs_subcomp_idx].name
        lhs_subcomp_dtype = _resolve_datatype(
            dtype.fields[lhs_subcomp_idx].datatype, ctxt
        )
        if not isinstance(lhs_subcomp_dtype, ir.DataTypeComponent):
            continue
        lhs_subcomp_type = lhs_subcomp_dtype.name or lhs_subcomp_name
        if lhs_port_idx >= len(lhs_subcomp_dtype.fields):
            continue
        lhs_port_name = lhs_subcomp_dtype.fields[lhs_port_idx].name

        # RHS: 1-level → bind to whole sub-component (use mem fetch fn)
        if (
            isinstance(rhs, _ExprRefField)
            and isinstance(rhs.base, TypeExprRefSelf)
        ):
            rhs_subcomp_idx = rhs.index
            if rhs_subcomp_idx >= len(dtype.fields):
                continue
            rhs_subcomp_name = dtype.fields[rhs_subcomp_idx].name
            rhs_subcomp_dtype = _resolve_datatype(
                dtype.fields[rhs_subcomp_idx].datatype, ctxt
            )
            if not isinstance(rhs_subcomp_dtype, ir.DataTypeComponent):
                continue
            rhs_type = rhs_subcomp_dtype.name or rhs_subcomp_name
            # Find first Memory field in the RHS component
            mem_field = next(
                (f for f in rhs_subcomp_dtype.fields
                 if isinstance(f.datatype, ir.DataTypeMemory)),
                None,
            )
            if mem_field is None:
                continue
            wire_fn = f"{rhs_type}_mem_fetch_{mem_field.name}"

        # RHS: 2-level → bind to specific callable export on sub-component
        elif (
            isinstance(rhs, _ExprRefField)
            and isinstance(rhs.base, _ExprRefField)
            and isinstance(rhs.base.base, TypeExprRefSelf)
        ):
            rhs_subcomp_idx = rhs.base.index
            rhs_export_idx = rhs.index
            if rhs_subcomp_idx >= len(dtype.fields):
                continue
            rhs_subcomp_name = dtype.fields[rhs_subcomp_idx].name
            rhs_subcomp_dtype = _resolve_datatype(
                dtype.fields[rhs_subcomp_idx].datatype, ctxt
            )
            if not isinstance(rhs_subcomp_dtype, ir.DataTypeComponent):
                continue
            rhs_type = rhs_subcomp_dtype.name or rhs_subcomp_name
            if rhs_export_idx >= len(rhs_subcomp_dtype.fields):
                continue
            export_name = rhs_subcomp_dtype.fields[rhs_export_idx].name
            wire_fn = f"{rhs_type}_{export_name}"
        else:
            continue

        results.append(
            (lhs_subcomp_name, lhs_port_name, lhs_subcomp_type,
             rhs_subcomp_name, rhs_type, wire_fn)
        )

    return results


class _Writer:
    """Small helper for indented C code generation."""

    def __init__(self):
        self._buf = io.StringIO()
        self._indent = 0

    def line(self, text: str = "") -> "_Writer":
        prefix = "    " * self._indent
        self._buf.write(f"{prefix}{text}\n")
        return self

    def blank(self) -> "_Writer":
        self._buf.write("\n")
        return self

    def indent(self) -> "_Writer":
        self._indent += 1
        return self

    def dedent(self) -> "_Writer":
        self._indent = max(0, self._indent - 1)
        return self

    def getvalue(self) -> str:
        return self._buf.getvalue()


# ---------------------------------------------------------------------------
# CEmitPass
# ---------------------------------------------------------------------------

class CEmitPass(SwPass):
    """Emit ``.h`` / ``.c`` files for each component in SwContext."""

    def run(self, ctxt: SwContext) -> SwContext:
        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, ir.DataTypeComponent):
                continue
            header = self._emit_header(type_name, dtype, ctxt)
            source = self._emit_source(type_name, dtype, ctxt)
            abi_sidecar = self._emit_abi_sidecar(type_name, dtype, ctxt)
            ctxt.output_files.append((f"{type_name}.h", header))
            ctxt.output_files.append((f"{type_name}.c", source))
            ctxt.output_files.append((f"{type_name}_abi.py", abi_sidecar))
        return ctxt

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _emit_header(
        self, name: str, dtype: ir.DataTypeComponent, ctxt: SwContext
    ) -> str:
        w = _Writer()
        guard = f"_{name.upper()}_H"
        w.line(f"#ifndef {guard}")
        w.line(f"#define {guard}")
        w.blank()
        w.line("#include <stdint.h>")
        w.line("#include <stddef.h>")
        w.line("#include <setjmp.h>")
        w.blank()
        w.line("#ifndef ZUSPEC_API")
        w.line("#  ifdef _WIN32")
        w.line("#    define ZUSPEC_API __declspec(dllexport)")
        w.line("#  else")
        w.line("#    define ZUSPEC_API __attribute__((visibility(\"default\")))")
        w.line("#  endif")
        w.line("#endif")
        w.blank()

        fmeta = _collect_field_meta(dtype, ctxt)

        # Include indexed pool header if any indexed_pool fields are present
        has_pool = any(m.kind == "indexed_pool" for m in fmeta.values())
        if has_pool:
            w.line("#include \"zsp_indexed_pool.h\"")
            w.blank()

        # Include memory header if any memory fields are present
        has_memory = any(m.kind == "memory" for m in fmeta.values())
        if has_memory:
            w.line("#include \"zsp_memory.h\"")
            w.blank()

        # Include sub-component headers
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "component":
                w.line(f"#include \"{m.comp_type}.h\"")
        if any(m.kind == "component" for m in fmeta.values()):
            w.blank()

        # Emit inline typedefs for Python dataclasses used as const() fields
        seen_py_structs: set = set()
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "py_struct" and m.py_struct_cls is not None:
                struct_name = m.comp_type
                if struct_name not in seen_py_structs:
                    seen_py_structs.add(struct_name)
                    _emit_py_struct_typedef(m.py_struct_cls, w)
        if seen_py_structs:
            w.blank()

        # Emit action struct typedefs used by coroutine locals of this component
        self._emit_action_typedefs(name, ctxt, w)

        # Forward-declare the struct typedef, then emit the full struct body
        # so that other .h files that include this one can embed the type by value.
        w.line(f"typedef struct {name}_s {name}_t;")
        w.blank()

        # Full struct definition (must be in header for sub-component embedding)
        nodes = ctxt.sw_nodes.get(name, [])
        self._emit_struct_def(name, dtype, nodes, fmeta, ctxt, w)
        w.blank()

        # Callable port typedefs
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "callable_port":
                arg_bits = m.callable_arg_bits or [32]
                args_str = ", ".join(f"uint{b}_t" for b in arg_bits)
                w.line(
                    f"typedef uint{m.callable_ret_bits}_t "
                    f"(*{name}_{field.name}_fn_t)(void *ud, {args_str});"
                )
        w.blank()

        # Core lifecycle declarations
        w.line(f"ZUSPEC_API void {name}_init({name}_t *self);")
        w.line(f"ZUSPEC_API void {name}_run({name}_t *self);")
        w.blank()

        # Field accessor declarations
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "plain" and m.accessible:
                w.line(
                    f"ZUSPEC_API {m.c_type} {name}_get_{field.name}({name}_t *self);"
                )
                w.line(
                    f"ZUSPEC_API void {name}_set_{field.name}({name}_t *self, {m.c_type} val);"
                )

        # IndexedRegFile accessor declarations
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "indexed_regfile":
                idx_t = f"uint{_round_to_std_bits(m.idx_bits)}_t"
                elem_t = f"uint{_round_to_std_bits(m.elem_bits)}_t"
                w.line(
                    f"ZUSPEC_API {elem_t} {name}_{field.name}_get({name}_t *self, {idx_t} idx);"
                )
                w.line(
                    f"ZUSPEC_API void {name}_{field.name}_set({name}_t *self, {idx_t} idx, {elem_t} val);"
                )
                w.line(
                    f"ZUSPEC_API void {name}_{field.name}_read_all({name}_t *self, {elem_t} *out, uint32_t count);"
                )

        # Callable port binder declarations
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "callable_port":
                w.line(
                    f"ZUSPEC_API void {name}_bind_{field.name}("
                    f"{name}_t *self, "
                    f"{name}_{field.name}_fn_t fn, void *ud);"
                )

        # Memory backdoor accessor declarations + callable-port-compatible fetch
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "memory":
                w.line(
                    f"ZUSPEC_API uint64_t {name}_mem_read_{field.name}"
                    f"({name}_t *self, uint32_t addr);"
                )
                w.line(
                    f"ZUSPEC_API void {name}_mem_write_{field.name}"
                    f"({name}_t *self, uint32_t addr, uint64_t data);"
                )
                ret_t = f"uint{_round_to_std_bits(m.elem_bits)}_t"
                w.line(
                    f"{ret_t} {name}_mem_fetch_{field.name}(void *ud, uint32_t addr);"
                )

        # Sub-component pointer accessor declarations
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "component":
                w.line(
                    f"ZUSPEC_API {m.comp_type}_t *{name}_ptr_{field.name}({name}_t *self);"
                )

        w.blank()
        w.line(f"#endif /* {guard} */")
        return w.getvalue()

    # ------------------------------------------------------------------
    # Source
    # ------------------------------------------------------------------

    def _emit_source(
        self, name: str, dtype: ir.DataTypeComponent, ctxt: SwContext
    ) -> str:
        w = _Writer()
        w.line(f'#include "{name}.h"')
        w.line('#include "zsp_types.h"')
        w.blank()

        nodes = ctxt.sw_nodes.get(name, [])

        # Fifo declarations (struct members go into component struct body)
        fmeta = _collect_field_meta(dtype, ctxt)

        # Include indexed pool header if any indexed_pool fields exist
        has_pool = any(m.kind == "indexed_pool" for m in fmeta.values())
        if has_pool:
            w.line('#include "zsp_indexed_pool.h"')
            w.blank()

        has_memory = any(m.kind == "memory" for m in fmeta.values())
        if has_memory:
            w.line('#include "zsp_memory.h"')
            w.line('#include "zsp_alloc.h"')
            w.line('#include "zsp_init_ctxt.h"')
            w.blank()
        has_coroutine = any(isinstance(n, SwCoroutineFrame) for n in nodes)
        if has_coroutine:
            w.line('#include "zsp_timebase.h"')
            w.blank()

        # Hide all symbols by default; only ZUSPEC_API functions are exported
        w.line("#pragma GCC visibility push(hidden)")
        w.blank()

        # (struct body is in the .h for sub-component embedding compatibility)

        # Func-ptr structs
        for node in nodes:
            if isinstance(node, SwFuncPtrStruct):
                self._emit_func_ptr_struct(node, w)
                w.blank()

        # Coroutine locals typedefs and function bodies must come BEFORE
        # run function references the task functions
        for node in nodes:
            if isinstance(node, SwCoroutineFrame):
                self._emit_coroutine_locals_typedef(node, ctxt, w)
                w.blank()
        for node in nodes:
            if isinstance(node, SwCoroutineFrame):
                self._emit_coroutine(node, ctxt, w)
                w.blank()

        # init function
        self._emit_init_fn(name, dtype, nodes, ctxt, w)
        w.blank()

        # run function
        self._emit_run_fn(name, dtype, nodes, ctxt, w)
        w.blank()

        # Field accessors
        self._emit_field_accessors(name, dtype, fmeta, ctxt, w)

        # IndexedRegFile accessors
        self._emit_regfile_accessors(name, dtype, fmeta, ctxt, w)

        # Memory backdoor read/write
        self._emit_backdoor_memory_api(name, dtype, fmeta, ctxt, w)

        # Sub-component pointer accessors
        self._emit_subcomp_accessors(name, dtype, fmeta, w)

        # Callable port binders
        self._emit_port_binders(name, dtype, fmeta, ctxt, w)

        # Scheduler
        for node in nodes:
            if isinstance(node, SwSchedulerNode):
                self._emit_scheduler(name, node, ctxt, w)
                w.blank()

        # Sync functions
        for func in dtype.functions:
            if getattr(func, "metadata", {}).get("sync_convertible"):
                self._emit_sync_function(name, func, ctxt, w)
                w.blank()

        # Mutex acquire/release
        for node in nodes:
            if isinstance(node, SwMutexAcquire):
                self._emit_mutex_acquire(name, node, w)
                w.blank()
            elif isinstance(node, SwMutexRelease):
                self._emit_mutex_release(name, node, w)
                w.blank()

        # Indexed select
        for node in nodes:
            if isinstance(node, SwIndexedSelect):
                self._emit_indexed_select(name, node, w)
                w.blank()

        w.line("#pragma GCC visibility pop")
        w.blank()

        return w.getvalue()

    # ------------------------------------------------------------------
    # Action typedefs
    # ------------------------------------------------------------------

    def _emit_action_typedefs(self, comp_name: str, ctxt: SwContext, w) -> None:
        """Emit ``typedef struct { ... } ActionName_t;`` for every DataTypeAction
        referenced by coroutine locals or inline-declared action vars."""
        emitted: set = set()

        def _emit_if_new(action_type: "ir.DataTypeAction") -> None:
            if action_type.name not in emitted:
                emitted.add(action_type.name)
                self._emit_action_typedef(action_type, ctxt, w)

        for node in ctxt.sw_nodes.get(comp_name, []):
            # From persistent locals struct (vars that cross suspension points)
            if hasattr(node, 'locals_struct'):
                for local_var in node.locals_struct:
                    vt = getattr(local_var, 'var_type', None)
                    if isinstance(vt, ir.DataTypeAction):
                        _emit_if_new(vt)
            # From inline continuation stmts (vars that don't cross suspension points)
            if hasattr(node, 'continuations'):
                for cont in node.continuations:
                    for vt in _collect_action_type_hints(cont.stmts).values():
                        _emit_if_new(vt)
        if emitted:
            w.blank()

    def _emit_action_typedef(self, action: ir.DataTypeAction, ctxt: SwContext, w) -> None:
        """Emit a C struct typedef for a single action type."""
        aname = action.name
        w.line(f"typedef struct {{")
        for field in action.fields:
            if field.name == 'comp':
                continue  # comp is passed as parameter, not embedded in struct
            c_type = _c_type(field.datatype, ctxt)
            w.line(f"    {c_type} {field.name};")
        w.line(f"}} {aname}_t;")
        w.blank()

    # ------------------------------------------------------------------
    # Struct definition
    # ------------------------------------------------------------------

    def _emit_struct_def(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        nodes: list,
        fmeta: Dict[str, _FieldMeta],
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        w.line(f"struct {name}_s {{")
        w.indent()
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None:
                continue
            if m.kind == "skip":
                w.line(f"/* skipped: {field.name} (untyped Python int) */")
            elif m.kind == "plain":
                w.line(f"{m.c_type} {field.name};")
            elif m.kind == "indexed_regfile":
                w.line(
                    f"uint{_round_to_std_bits(m.elem_bits)}_t {field.name}[{m.depth}];"
                    f"  /* IndexedRegFile depth={m.depth} */"
                )
            elif m.kind == "indexed_pool":
                w.line(f"zsp_indexed_pool_t {field.name};  /* IndexedPool depth={m.depth} */")
            elif m.kind == "memory":
                w.line(f"zsp_memory_t {field.name};  /* Memory[{m.elem_bits}b] size={m.mem_size} */")
            elif m.kind == "component":
                w.line(f"{m.comp_type}_t {field.name};  /* sub-component */")
            elif m.kind == "py_struct":
                w.line(f"{m.comp_type}_t {field.name};  /* Python dataclass */")
            elif m.kind == "callable_port":
                ret_t = f"uint{m.callable_ret_bits}_t"
                arg_bits = m.callable_arg_bits or [32]
                args_str = ", ".join(f"uint{b}_t" for b in arg_bits)
                w.line(
                    f"{ret_t} (*{field.name})(void *ud, {args_str});"
                )
                w.line(f"void *{field.name}_ud;")
        # FIFO fields
        for node in nodes:
            if isinstance(node, SwFifo):
                elem = _c_type(node.element_type, ctxt)
                w.line(f"/* fifo: {node.field_name} <{elem}> */")
                w.line(f"zsp_fifo_t {node.field_name}_fifo;")
        # Halt slot (always present so Python can install a halt callback)
        w.line("/* halt slot: Python installs a longjmp callback */")
        w.line(f"void (*_halt_fn)(void *ud, int exit_code);")
        w.line(f"void *_halt_ud;")
        w.line(f"jmp_buf _halt_jmp;")
        w.dedent()
        w.line("};")

    # ------------------------------------------------------------------
    # init function
    # ------------------------------------------------------------------

    def _emit_init_fn(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        nodes: list,
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        fmeta = _collect_field_meta(dtype, ctxt)
        # Check if any memory fields need initialisation (they need an alloc ctxt).
        has_memory = any(m.kind == "memory" for m in fmeta.values())
        w.line(f"ZUSPEC_API void {name}_init({name}_t *self) {{")
        w.indent()
        if has_memory:
            w.line("zsp_alloc_t _alloc;")
            w.line("zsp_init_ctxt_t _ctxt = {0};")
            w.line("zsp_alloc_malloc_init(&_alloc);")
            w.line("_ctxt.alloc = &_alloc;")
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "component":
                w.line(f"{m.comp_type}_init(&self->{field.name});")
            elif m and m.kind == "indexed_pool":
                w.line(f"zsp_indexed_pool_init(&self->{field.name}, {m.depth});")
            elif m and m.kind == "memory":
                w.line(
                    f'zsp_memory_init(&_ctxt, &self->{field.name}, "{field.name}", NULL,'
                    f" {m.mem_size}, {m.elem_bits});"
                )
        for node in nodes:
            if isinstance(node, SwFifo):
                depth = node.depth or 16
                w.line(f"zsp_fifo_init(&self->{node.field_name}_fifo, {depth});")
        # Internal port wiring from bind_map
        for wiring in _decode_bind_wirings(dtype, ctxt):
            lhs_sub, lhs_port, lhs_type, rhs_sub, _rhs_type, wire_fn = wiring
            w.line(
                f"{lhs_type}_bind_{lhs_port}(&self->{lhs_sub}, {wire_fn}, &self->{rhs_sub});"
            )
        w.dedent()
        w.line("}")

    # ------------------------------------------------------------------
    # run function
    # ------------------------------------------------------------------

    def _emit_run_fn(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        nodes: list,
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        """Emit `{name}_run()` which drives any process coroutines via setjmp.

        If the component has no processes of its own but contains sub-component
        fields, delegate to each sub-component's run() function so that a parent
        testbench (like RVTestbench) can drive its children.
        """
        fmeta = _collect_field_meta(dtype, ctxt)
        sched_nodes = [n for n in nodes if isinstance(n, SwSchedulerNode)]
        coroutine_frames = [n for n in nodes if isinstance(n, SwCoroutineFrame)]
        sub_comp_fields = [
            (field.name, m.comp_type)
            for field in dtype.fields
            for m in [fmeta.get(field.name)]
            if m is not None and m.kind == "component"
        ]
        w.line(f"ZUSPEC_API void {name}_run({name}_t *self) {{")
        w.indent()
        w.line("if (setjmp(self->_halt_jmp) != 0) { return; }")
        if sched_nodes:
            w.line(f"{name}_sched(self);")
        elif coroutine_frames:
            # Drive each process coroutine to completion (flat, no real time)
            for frame in coroutine_frames:
                fn = frame.func_name
                w.line(f"{{")
                w.indent()
                w.line(f"{fn}_locals_t locals = {{{{0}}}};")
                w.line(f"zsp_thread_t thread = {{{{0}}}};")
                w.line(f"zsp_timebase_t tb = {{{{0}}}};")
                w.line(f"locals.self = self;")
                w.line(f"thread.leaf = (zsp_frame_t *)&locals;")
                w.line(f"{fn}_task(&tb, &thread, 0);")
                w.dedent()
                w.line(f"}}")
        elif sub_comp_fields:
            # No own processes — delegate to sub-components
            for field_name, comp_type in sub_comp_fields:
                w.line(f"{comp_type}_run(&self->{field_name});")
        else:
            w.line("/* no processes — nothing to run */")
        w.dedent()
        w.line("}")

    # ------------------------------------------------------------------
    # Field accessors
    # ------------------------------------------------------------------

    def _emit_field_accessors(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        fmeta: Dict[str, _FieldMeta],
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        """Emit getter/setter for each plain accessible field."""
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or not (m.kind == "plain" and m.accessible):
                continue
            w.line(
                f"ZUSPEC_API {m.c_type} {name}_get_{field.name}({name}_t *self) {{"
            )
            w.indent()
            w.line(f"return self->{field.name};")
            w.dedent()
            w.line("}")
            w.blank()
            w.line(
                f"ZUSPEC_API void {name}_set_{field.name}({name}_t *self, {m.c_type} val) {{"
            )
            w.indent()
            w.line(f"self->{field.name} = val;")
            w.dedent()
            w.line("}")
            w.blank()

    # ------------------------------------------------------------------
    # Callable port binders
    # ------------------------------------------------------------------

    def _emit_regfile_accessors(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        fmeta: Dict[str, _FieldMeta],
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        """Emit get/set/read_all accessors for each IndexedRegFile field."""
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "indexed_regfile":
                continue
            idx_t = f"uint{_round_to_std_bits(m.idx_bits)}_t"
            elem_t = f"uint{_round_to_std_bits(m.elem_bits)}_t"
            mask = m.depth - 1
            # get
            w.line(
                f"ZUSPEC_API {elem_t} {name}_{field.name}_get("
                f"{name}_t *self, {idx_t} idx) {{"
            )
            w.indent()
            w.line(f"return self->{field.name}[idx & {mask}];")
            w.dedent()
            w.line("}")
            w.blank()
            # set
            w.line(
                f"ZUSPEC_API void {name}_{field.name}_set("
                f"{name}_t *self, {idx_t} idx, {elem_t} val) {{"
            )
            w.indent()
            w.line(f"self->{field.name}[idx & {mask}] = val;")
            w.dedent()
            w.line("}")
            w.blank()
            # read_all
            w.line(
                f"ZUSPEC_API void {name}_{field.name}_read_all("
                f"{name}_t *self, {elem_t} *out, uint32_t count) {{"
            )
            w.indent()
            w.line(f"uint32_t n = count < {m.depth}u ? count : {m.depth}u;")
            w.line(f"uint32_t i;")
            w.line(f"for (i = 0; i < n; i++) out[i] = self->{field.name}[i];")
            w.dedent()
            w.line("}")
            w.blank()

    # ------------------------------------------------------------------
    # Callable port binders (original section)
    # ------------------------------------------------------------------

    def _emit_backdoor_memory_api(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        fmeta: Dict[str, _FieldMeta],
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        """Emit backdoor read/write functions and a callable-port-compatible
        fetch function for each Memory field.

        Generated signatures::

            uint64_t {Name}_mem_read_{field}({Name}_t *self, uint32_t addr);
            void     {Name}_mem_write_{field}({Name}_t *self, uint32_t addr, uint64_t data);
            {elem_t} {Name}_mem_fetch_{field}(void *ud, uint32_t addr);  /* internal wiring */
        """
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "memory":
                continue
            ret_t = f"uint{_round_to_std_bits(m.elem_bits)}_t"
            # read (ZUSPEC_API — Python backdoor)
            w.line(
                f"ZUSPEC_API uint64_t {name}_mem_read_{field.name}"
                f"({name}_t *self, uint32_t addr) {{"
            )
            w.indent()
            w.line(f"return zsp_memory_read(&self->{field.name}, addr);")
            w.dedent()
            w.line("}")
            w.blank()
            # write (ZUSPEC_API — Python backdoor)
            w.line(
                f"ZUSPEC_API void {name}_mem_write_{field.name}"
                f"({name}_t *self, uint32_t addr, uint64_t data) {{"
            )
            w.indent()
            w.line(f"zsp_memory_write(&self->{field.name}, addr, data);")
            w.dedent()
            w.line("}")
            w.blank()
            # fetch — callable-port-compatible (void *ud, not ZUSPEC_API)
            w.line(
                f"{ret_t} {name}_mem_fetch_{field.name}(void *ud, uint32_t addr) {{"
            )
            w.indent()
            w.line(f"{name}_t *self = ({name}_t *)ud;")
            w.line(f"return ({ret_t})zsp_memory_read(&self->{field.name}, addr);")
            w.dedent()
            w.line("}")
            w.blank()

    # ------------------------------------------------------------------
    # Sub-component pointer accessors
    # ------------------------------------------------------------------

    def _emit_subcomp_accessors(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        fmeta: Dict[str, _FieldMeta],
        w: _Writer,
    ) -> None:
        """Emit `{Name}_ptr_{field}()` functions that return a pointer to each
        embedded sub-component, so Python can build a sub-component proxy."""
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "component":
                continue
            w.line(
                f"ZUSPEC_API {m.comp_type}_t *{name}_ptr_{field.name}({name}_t *self) {{"
            )
            w.indent()
            w.line(f"return &self->{field.name};")
            w.dedent()
            w.line("}")
            w.blank()

    # ------------------------------------------------------------------
    # Callable port binders (original section)
    # ------------------------------------------------------------------

    def _emit_port_binders(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        fmeta: Dict[str, _FieldMeta],
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        """Emit `bind_{port}` functions for each CallablePort field."""
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "callable_port":
                continue
            fn_type = f"{name}_{field.name}_fn_t"
            w.line(
                f"ZUSPEC_API void {name}_bind_{field.name}("
                f"{name}_t *self, {fn_type} fn, void *ud) {{"
            )
            w.indent()
            w.line(f"self->{field.name} = fn;")
            w.line(f"self->{field.name}_ud = ud;")
            w.dedent()
            w.line("}")
            w.blank()

    # ------------------------------------------------------------------
    # ABI sidecar
    # ------------------------------------------------------------------

    def _emit_abi_sidecar(
        self,
        name: str,
        dtype: ir.DataTypeComponent,
        ctxt: SwContext,
    ) -> str:
        """Emit a Python module that configures ctypes argtypes/restype.

        The generated file is named ``{name}_abi.py`` and exports a single
        ``configure(lib)`` function.  ``CObjFactory`` imports this after
        loading the shared library.
        """
        fmeta = _collect_field_meta(dtype, ctxt)
        lines: List[str] = [
            "\"\"\"Auto-generated ctypes ABI configuration for " + name + ".\"\"\"\n",
            "import ctypes\n",
            "\n",
            "def configure(lib):\n",
            f"    \"\"\"Bind argtypes/restype for all public {name} functions.\"\"\"\n",
        ]

        def _ctypes_int(bits: int, signed: bool = False) -> str:
            rounded = _round_to_std_bits(bits)
            if signed:
                return {8: "c_int8", 16: "c_int16", 32: "c_int32", 64: "c_int64"}.get(rounded, "c_int32")
            return {8: "c_uint8", 16: "c_uint16", 32: "c_uint32", 64: "c_uint64"}.get(rounded, "c_uint32")

        ptr = "ctypes.c_void_p"

        def _fn(fn_name: str, argtypes: List[str], restype: str) -> None:
            at = ", ".join(argtypes)
            lines.append(f"    lib.{fn_name}.argtypes = [{at}]\n")
            lines.append(f"    lib.{fn_name}.restype = {restype}\n")

        # _init
        _fn(f"{name}_init", [ptr], "None")
        # _run
        _fn(f"{name}_run", [ptr], "None")

        # field accessors
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or not (m.kind == "plain" and m.accessible):
                continue
            if isinstance(field.datatype, ir.DataTypeInt):
                ctype = _ctypes_int(field.datatype.bits, field.datatype.signed)
            else:
                ctype = "c_uint32"
            _fn(f"{name}_get_{field.name}", [ptr], f"ctypes.{ctype}")
            _fn(f"{name}_set_{field.name}", [ptr, f"ctypes.{ctype}"], "None")

        # IndexedRegFile accessors
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "indexed_regfile":
                continue
            idx_ct = _ctypes_int(m.idx_bits)
            elem_ct = _ctypes_int(m.elem_bits)
            _fn(
                f"{name}_{field.name}_get",
                [ptr, f"ctypes.{idx_ct}"],
                f"ctypes.{elem_ct}",
            )
            _fn(
                f"{name}_{field.name}_set",
                [ptr, f"ctypes.{idx_ct}", f"ctypes.{elem_ct}"],
                "None",
            )
            _fn(
                f"{name}_{field.name}_read_all",
                [ptr, "ctypes.c_void_p", "ctypes.c_uint32"],
                "None",
            )

        # callable port binders
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "callable_port":
                continue
            _fn(
                f"{name}_bind_{field.name}",
                [ptr, ptr, ptr],
                "None",
            )

        # memory backdoor accessors
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "memory":
                continue
            _fn(
                f"{name}_mem_read_{field.name}",
                [ptr, "ctypes.c_uint32"],
                "ctypes.c_uint64",
            )
            _fn(
                f"{name}_mem_write_{field.name}",
                [ptr, "ctypes.c_uint32", "ctypes.c_uint64"],
                "None",
            )

        # sub-component pointer accessors
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None or m.kind != "component":
                continue
            _fn(f"{name}_ptr_{field.name}", [ptr], ptr)

        lines.append("\n")
        return "".join(lines)


    def _emit_scheduler(
        self,
        comp_name: str,
        sched: SwSchedulerNode,
        ctxt: SwContext,
        w: _Writer,
    ) -> None:
        w.line(f"static void {comp_name}_sched({comp_name}_t *self) {{")
        w.indent()
        if sched.root:
            self._emit_sched_node(comp_name, sched.root, ctxt, w)
        w.dedent()
        w.line("}")

    def _emit_sched_node(self, comp_name: str, node, ctxt: SwContext, w: _Writer) -> None:
        if isinstance(node, SwSeqBlock):
            self._emit_seq_block(comp_name, node, ctxt, w)
        elif isinstance(node, SwParBlock):
            self._emit_par_block(comp_name, node, ctxt, w)
        elif isinstance(node, SwSelectNode):
            self._emit_select_node(comp_name, node, ctxt, w)
        elif isinstance(node, SwActionExec):
            self._emit_action_exec(comp_name, node, w)

    def _emit_seq_block(
        self, comp_name: str, block: SwSeqBlock, ctxt: SwContext, w: _Writer
    ) -> None:
        w.line("/* seq */")
        for child in block.children:
            self._emit_sched_node(comp_name, child, ctxt, w)

    def _emit_par_block(
        self, comp_name: str, block: SwParBlock, ctxt: SwContext, w: _Writer
    ) -> None:
        w.line(f"zsp_par_block_t _par; zsp_par_block_init(&_par, {len(block.children)});")
        for i, child in enumerate(block.children):
            w.line(f"/* fork {i} */")
            self._emit_sched_node(comp_name, child, ctxt, w)
        w.line("zsp_par_block_join(&_par);")

    def _emit_select_node(
        self, comp_name: str, sel: SwSelectNode, ctxt: SwContext, w: _Writer
    ) -> None:
        branches = sel.branches
        w.line(f"/* select — {len(branches)} branches */")
        w.line(f"zsp_select_t _sel; zsp_select_init(&_sel, {len(branches)});")
        for i, branch in enumerate(branches):
            w.line(f"/* branch {i} (weight={branch.weight}) */")
            if branch.body is not None:
                self._emit_sched_node(comp_name, branch.body, ctxt, w)
        w.line("/* zsp_select_weighted_random(&_sel); */")

    def _emit_action_exec(
        self, comp_name: str, node: SwActionExec, w: _Writer
    ) -> None:
        action = node.action_type.name if node.action_type else "action"
        handle = node.handle_name or ""
        w.line(f"{action}_run(self);  /* handle: {handle} */")

    # ------------------------------------------------------------------
    # Sync function
    # ------------------------------------------------------------------

    def _emit_sync_function(
        self, comp_name: str, func: ir.Function, ctxt: SwContext, w: _Writer
    ) -> None:
        sg = StmtGenerator(py_globals=ctxt.py_globals)
        w.line(f"static void {comp_name}_{func.name}({comp_name}_t *self) {{")
        w.indent()
        for stmt in func.body:
            code = sg._gen_dm_stmt(stmt)
            if code.strip():
                for line in code.splitlines():
                    w.line(line)
        w.dedent()
        w.line("}")

    # ------------------------------------------------------------------
    # Coroutine
    # ------------------------------------------------------------------

    def _emit_coroutine_locals_typedef(
        self, frame: SwCoroutineFrame, ctxt: SwContext, w: _Writer
    ) -> None:
        """Emit just the locals struct typedef for a coroutine frame.

        Must be emitted before any function that references the locals type
        (e.g., the run function that initialises the frame).
        """
        fn_name = frame.func_name or "coroutine"
        comp_name = frame.comp_type_name or "Comp"
        w.line(f"typedef struct {{")
        w.indent()
        w.line("zsp_frame_t frame;")
        w.line(f"{comp_name}_t *self;")
        for lv in (frame.locals_struct or []):
            c_t = _c_type(lv.var_type, ctxt) if lv.var_type else "int"
            w.line(f"{c_t} {lv.var_name};")
        w.dedent()
        w.line(f"}} {fn_name}_locals_t;")

    def _emit_coroutine(
        self, frame: SwCoroutineFrame, ctxt: SwContext, w: _Writer
    ) -> None:
        """Emit the coroutine task function (locals typedef is emitted separately)."""
        fn_name = frame.func_name or "coroutine"
        comp_name = frame.comp_type_name or "Comp"

        # coroutine function signature
        w.line(f"static zsp_frame_t *{fn_name}_task(")
        w.indent()
        w.line("zsp_timebase_t *tb,")
        w.line("zsp_thread_t *thread,")
        w.line("int idx) {")
        w.dedent()
        w.indent()
        w.line(f"{fn_name}_locals_t *locals = ({fn_name}_locals_t *)thread->leaf;")
        w.line(f"{comp_name}_t *self = locals->self;")
        w.line("zsp_frame_t *ret = thread->leaf;")
        w.blank()
        w.line("switch (idx) {")
        w.indent()

        lsn = {lv.var_name for lv in (frame.locals_struct or [])}
        for cont in frame.continuations:
            component = ctxt.type_m.get(comp_name) if comp_name else None
            self._emit_continuation(fn_name, cont, ctxt, w, component=component, locals_struct_names=lsn)

        w.dedent()
        w.line("}")  # switch
        w.line("return ret;")
        w.dedent()
        w.line("}")  # function

    def _emit_continuation(
        self, fn_name: str, cont: SwContinuation, ctxt: SwContext, w: _Writer,
        component=None,
        locals_struct_names=None,
    ) -> None:
        _lsn = set(locals_struct_names) if locals_struct_names else set()
        sg = StmtGenerator(
            component=component,
            ctxt=ctxt,
            py_globals=ctxt.py_globals,
            locals_struct_names=_lsn,
        )
        w.line(f"case {cont.index}: {{")
        w.indent()

        # Declare any unresolved local variable names, using the correct type.
        # Action vars (StmtAnnAssign with DataTypeAction ir_type) get their struct type;
        # names used as '->field' pointer bases get _zsp_stub_t *;
        # all other vars fall back to uint32_t.
        #
        # Note: stub_ptr_names may include names excluded from unresolved (pure attr bases
        # like `claim` in `claim->t->execute(...)`) — declare those separately.
        action_hints = _collect_action_type_hints(cont.stmts)
        stub_ptr_names = _collect_stub_ptr_names(cont.stmts)
        unresolved = _collect_unresolved_names(cont.stmts) - _lsn
        all_to_declare = unresolved | (stub_ptr_names - _lsn)
        for name in sorted(all_to_declare):
            if name in action_hints:
                struct_type = f"{action_hints[name].name}_t"
                w.line(f"{struct_type} {name} = {{{{0}}}};")
            elif name in stub_ptr_names:
                w.line(f"_zsp_stub_t *{name} = NULL;")
            else:
                w.line(f"uint32_t {name} = 0;")

        for stmt in cont.stmts:
            code = sg._gen_dm_stmt(stmt)
            if code.strip():
                for line in code.splitlines():
                    w.line(line)
        if cont.suspend is not None:
            self._emit_suspend_point(cont.suspend, cont.next_index, w)
        else:
            w.line("/* coroutine complete */")
            w.line("return NULL;")
        w.dedent()
        w.line("}")

    def _emit_suspend_point(
        self, sp: SwSuspendPoint, next_idx: Optional[int], w: _Writer
    ) -> None:
        if isinstance(sp, SwSuspendWait):
            dur = sp.duration_expr
            if dur is not None and hasattr(dur, "value"):
                w.line(f"zsp_timebase_wait(thread, ZSP_TIME_S({dur.value}));")
            else:
                w.line("zsp_timebase_wait(thread, ZSP_TIME_S(1));")
        elif isinstance(sp, SwSuspendFifoPop):
            w.line(f"if (!zsp_fifo_nb_pop(&self->{sp.fifo_field}_fifo, &tmp)) {{")
            w.indent()
            w.line("break;")
            w.dedent()
            w.line("}")
        elif isinstance(sp, SwSuspendFifoPush):
            w.line(f"zsp_fifo_push(&self->{sp.fifo_field}_fifo, val);")
        elif isinstance(sp, SwSuspendMutex):
            w.line(f"if (!zsp_mutex_try_acquire(&self->{sp.pool_field}_mutex)) {{")
            w.indent()
            w.line("break;")
            w.dedent()
            w.line("}")
        elif isinstance(sp, SwSuspendCall):
            # Synchronous callable port — the call is already emitted as an assignment
            # statement above.  Do NOT break: fall through to the next case so that
            # the rest of the coroutine body executes in the same invocation.
            if next_idx is not None:
                w.line(f"/* resume at index {next_idx} */")
            # intentional fall-through (no break)
            return

        if next_idx is not None:
            w.line(f"/* resume at index {next_idx} */")
        w.line("break;")

    # ------------------------------------------------------------------
    # Fifo declaration (inline within _emit_struct_def)
    # ------------------------------------------------------------------

    def _emit_fifo_decl(self, fifo: SwFifo, comp_name: str, w: _Writer) -> None:
        """Emit a FIFO field comment (actual field emitted in struct)."""
        w.line(f"/* fifo {comp_name}::{fifo.field_name} depth={fifo.depth} */")

    # ------------------------------------------------------------------
    # Func ptr struct
    # ------------------------------------------------------------------

    def _emit_func_ptr_struct(self, fps: SwFuncPtrStruct, w: _Writer) -> None:
        w.line(f"typedef struct {{")
        w.indent()
        for slot in fps.slots:
            w.line(f"void (*{slot.slot_name})(void *);")
        w.dedent()
        w.line(f"}} {fps.struct_name};")

    # ------------------------------------------------------------------
    # Mutex acquire / release
    # ------------------------------------------------------------------

    def _emit_mutex_acquire(self, comp_name: str, node: SwMutexAcquire, w: _Writer) -> None:
        pool = self._expr_name(node.pool_expr) or "mutex"
        var = node.out_var or "_unit"
        w.line(f"void {comp_name}_{pool}_acquire({comp_name}_t *self, int *{var}) {{")
        w.indent()
        w.line(f"*{var} = zsp_mutex_acquire(&self->{pool}_mutex);")
        w.dedent()
        w.line("}")

    def _emit_mutex_release(self, comp_name: str, node: SwMutexRelease, w: _Writer) -> None:
        pool = self._expr_name(node.pool_expr) or "mutex"
        unit = node.acquire_ref.out_var if node.acquire_ref else "_unit"
        w.line(f"void {comp_name}_{pool}_release({comp_name}_t *self, int {unit}) {{")
        w.indent()
        w.line(f"zsp_mutex_release(&self->{pool}_mutex, {unit});")
        w.dedent()
        w.line("}")

    # ------------------------------------------------------------------
    # Indexed select
    # ------------------------------------------------------------------

    def _emit_indexed_select(
        self, comp_name: str, node: SwIndexedSelect, w: _Writer
    ) -> None:
        pool = self._expr_name(node.pool_expr) or "pool"
        w.line(f"int {comp_name}_{pool}_select({comp_name}_t *self) {{")
        w.indent()
        w.line(f"return zsp_indexed_pool_acquire_random(&self->{pool});")
        w.dedent()
        w.line("}")

    def _expr_name(self, expr) -> Optional[str]:
        """Extract a best-effort name string from an expression."""
        if expr is None:
            return None
        if isinstance(expr, ir.ExprAttribute):
            return expr.attr
        if isinstance(expr, (ir.ExprRefLocal, ir.ExprRefUnresolved)):
            return expr.name
        return None

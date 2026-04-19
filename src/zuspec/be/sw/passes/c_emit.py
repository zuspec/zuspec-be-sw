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
    SwSuspendCompletion,
    SwSuspendFifoPop,
    SwSuspendFifoPush,
    SwSuspendMutex,
    SwSuspendPoint,
    SwSuspendSpawn,
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
    # Pseudo-variables used only for type-cast notation (e.g. zdc.u64(x)) — not real pointers.
    _PSEUDO_VARS = frozenset({"zdc"})
    names: Set[str] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, ir.ExprAttribute):
            if isinstance(node.value, ir.ExprRefUnresolved) and node.value.name not in _PSEUDO_VARS:
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


def _collect_action_type_hints(stmts: list) -> Dict[str, "ir.DataType"]:
    """Return {var_name: DataType} for every StmtAnnAssign that carries a typed ir_type.

    Covers DataTypeAction (inlined action struct vars) and DataTypeTupleReturn
    (tuple-unpack temp vars), both of which need non-uint32_t C declarations.
    """
    hints: Dict[str, Any] = {}
    for stmt in stmts:
        if isinstance(stmt, ir.StmtAnnAssign):
            ir_type = getattr(stmt, "ir_type", None)
            if isinstance(ir_type, (ir.DataTypeAction, ir.DataTypeTupleReturn)):
                tgt = getattr(stmt, "target", None)
                if isinstance(tgt, ir.ExprRefLocal):
                    hints[tgt.name] = ir_type
        for attr in ("body", "orelse"):
            children = getattr(stmt, attr, None)
            if isinstance(children, list):
                hints.update(_collect_action_type_hints(children))
    return hints


def _infer_local_types_from_assigns(stmts: list) -> Dict[str, str]:
    """Infer C type strings for local variables from their zdc.uN() / zdc.iN() assignment RHS.

    Returns {var_name: c_type_str} for variables assigned via type-cast notation,
    e.g. ``addr = zdc.uint64_t(0)`` → ``{"addr": "uint64_t"}``.
    """
    _zdc_types = {
        "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
        "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
        "uint8_t": "uint8_t", "uint16_t": "uint16_t",
        "uint32_t": "uint32_t", "uint64_t": "uint64_t",
        "int8_t": "int8_t", "int16_t": "int16_t",
        "int32_t": "int32_t", "int64_t": "int64_t",
    }
    hints: Dict[str, str] = {}
    for stmt in stmts:
        if isinstance(stmt, (ir.StmtAssign, ir.StmtAnnAssign)):
            value = getattr(stmt, "value", None)
            tgts = getattr(stmt, "targets", None) or [getattr(stmt, "target", None)]
            target_name = None
            if tgts and isinstance(tgts[0], (ir.ExprRefLocal, ir.ExprRefUnresolved)):
                target_name = tgts[0].name
            if target_name and isinstance(value, ir.ExprCall):
                func = value.func
                if (isinstance(func, ir.ExprAttribute)
                        and isinstance(func.value, ir.ExprRefUnresolved)
                        and func.value.name == "zdc"
                        and func.attr in _zdc_types):
                    hints[target_name] = _zdc_types[func.attr]
        for attr in ("body", "orelse"):
            children = getattr(stmt, attr, None)
            if isinstance(children, list):
                hints.update(_infer_local_types_from_assigns(children))
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
    if isinstance(dtype, ir.DataTypeTupleReturn):
        n = dtype.arity
        return f"_zsp_tuple{n}_t"
    return "void"


def _c_type_from_annotation(annotation_expr, ctxt: SwContext) -> str:
    """Convert an ``Arg.annotation`` (ExprConstant wrapping a Python type) to a C type string."""
    if annotation_expr is None:
        return "uint32_t"
    # annotation_expr is ExprConstant(value=<Python type>)
    py_type = getattr(annotation_expr, "value", None)
    if py_type is None:
        return "uint32_t"
    # Check for annotated integer (zdc.u32, zdc.u5, etc.)
    if _typing.get_origin(py_type) is _typing.Annotated:
        args = _typing.get_args(py_type)
        if args:
            meta = args[1] if len(args) > 1 else None
            if meta is not None and hasattr(meta, "width"):
                bits = meta.width
                if bits <= 8: bits = 8
                elif bits <= 16: bits = 16
                elif bits <= 32: bits = 32
                else: bits = 64
                signed = getattr(meta, "signed", False)
                return f"{'int' if signed else 'uint'}{bits}_t"
    # Enum type → uint32_t
    import enum as _enum
    if isinstance(py_type, type) and issubclass(py_type, _enum.IntEnum):
        return "uint32_t"
    # Named type present in type_m → {Name}_t
    if hasattr(py_type, "__name__"):
        name = py_type.__name__
        if name in ctxt.type_m:
            return f"{name}_t"
    return "uint32_t"


def _py_annotation_to_c(py_type: Any, ctxt: SwContext) -> str:
    """Convert a raw Python type annotation to a C type string.

    More powerful than ``_c_type_from_annotation`` because it receives the
    original Python type object (not an IR ``ExprConstant``) and can handle
    ``typing.Annotated`` directly.
    """
    if py_type is None:
        return "void"
    import typing as _t
    origin = _t.get_origin(py_type)
    if origin is _t.Annotated:
        args = _t.get_args(py_type)
        if len(args) >= 2:
            meta = args[1]
            if hasattr(meta, "width"):
                bits = meta.width
                if bits <= 8: bits = 8
                elif bits <= 16: bits = 16
                elif bits <= 32: bits = 32
                else: bits = 64
                signed = getattr(meta, "signed", False)
                return f"{'int' if signed else 'uint'}{bits}_t"
    import enum as _enum
    if isinstance(py_type, type) and issubclass(py_type, _enum.IntEnum):
        return "uint32_t"
    if py_type is type(None) or py_type is None:
        return "void"
    if hasattr(py_type, "__name__"):
        name = py_type.__name__
        if name in ctxt.type_m:
            return f"{name}_t"
        if name in ("int", "NoneType"):
            return "uint32_t" if name == "int" else "void"
    return "uint32_t"


def _get_protocol_method_hints(py_protocol: Any) -> Dict[str, Dict[str, Any]]:
    """Return per-method type hints for a Python Protocol class.

    Returns a dict ``{method_name: {"param": type, ..., "return": type}}``.
    Uses ``include_extras=True`` to preserve ``typing.Annotated`` metadata
    (needed to distinguish ``zdc.uint64_t`` from plain ``int``).
    """
    import typing as _t
    import inspect as _inspect
    result: Dict[str, Dict[str, Any]] = {}
    for name, member in _inspect.getmembers(py_protocol, predicate=_inspect.isfunction):
        if name.startswith("_"):
            continue
        try:
            hints = _t.get_type_hints(member, include_extras=True)
            result[name] = hints
        except Exception:
            result[name] = {}
    return result


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
        "mem_size", "comp_type", "py_struct_cls", "elem_type_name",
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
        self.elem_type_name: str = ""  # for kind=="claim_pool": element type name
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

        if field.kind in (ir.FieldKind.ProtocolPort, ir.FieldKind.ProtocolExport):
            # Resolve protocol type name from Python hint or IR
            proto_name = None
            hint = py_hints.get(field.name)
            if hint is not None and hasattr(hint, "__name__"):
                proto_name = hint.__name__
            if proto_name is None and isinstance(field.datatype, ir.DataTypeRef):
                resolved = ctxt.type_m.get(field.datatype.ref_name)
                if isinstance(resolved, ir.DataTypeProtocol):
                    proto_name = resolved.name or field.datatype.ref_name
                else:
                    proto_name = field.datatype.ref_name
            if proto_name is None:
                proto_name = field.name
            m.kind = "method_port" if field.kind == ir.FieldKind.ProtocolPort else "method_export"
            m.comp_type = f"{proto_name}_t"
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

            if ref == "ClaimPool":
                m.kind = "claim_pool"
                # Recover element type name from Python hint ClaimPool[ElemType]
                hint = py_hints.get(field.name)
                if hint is not None:
                    type_args = _typing.get_args(hint)
                    if type_args and isinstance(type_args[0], type):
                        m.elem_type_name = type_args[0].__name__
                m.accessible = False
                result[field.name] = m
                continue

        if isinstance(field.datatype, ir.DataTypeClaimPool):
            m.kind = "claim_pool"
            m.elem_type_name = field.datatype.elem_type_name
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

    from zuspec.ir.core.expr import TypeExprRefSelf, ExprRefField as _ExprRefField

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


# ---------------------------------------------------------------------------
# Time-unit helpers for LT-mode wait codegen
# ---------------------------------------------------------------------------

_TIME_UNIT_PS: Dict[str, int] = {
    "ps": 1,
    "ns": 1_000,
    "us": 1_000_000,
    "ms": 1_000_000_000,
    "s":  1_000_000_000_000,
}


def _duration_to_ps_str(dur) -> str:
    """Convert a duration IR ``Expr`` to a C picosecond literal or expression.

    Handles:
    - ``None``                             → ``"0"``
    - ``ExprConstant(value=N)``            → ``str(N)``  (treated as raw ps)
    - ``ExprCall(func=ns|us|ms|s|ps, N)``  → constant-folded picosecond literal
    """
    if dur is None:
        return "0"
    if isinstance(dur, ir.ExprConstant) and isinstance(dur.value, (int, float)):
        return str(int(dur.value))
    if isinstance(dur, ir.ExprCall) and dur.args:
        fn = dur.func
        fn_name: Optional[str] = None
        if isinstance(fn, ir.ExprRefUnresolved):
            fn_name = fn.name
        elif isinstance(fn, ir.ExprAttribute):
            fn_name = fn.attr
        if fn_name in _TIME_UNIT_PS:
            arg = dur.args[0]
            mult = _TIME_UNIT_PS[fn_name]
            if isinstance(arg, ir.ExprConstant) and isinstance(arg.value, (int, float)):
                return str(int(arg.value) * mult)
            return f"(uint64_t)({arg}) * {mult}ULL"
    # Fallback: emit raw value if available
    if hasattr(dur, "value"):
        return str(dur.value)
    return "0"


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
        # Collect all unique SwFuncPtrStructs across all components and emit
        # a shared protocol header (e.g. IMemory.h) for each one so that
        # multiple component headers can include it without redefining the type.
        seen_fps: dict = {}  # struct_name -> SwFuncPtrStruct
        for type_name, nodes in ctxt.sw_nodes.items():
            for node in nodes:
                if isinstance(node, SwFuncPtrStruct) and node.struct_name:
                    # Strip trailing _t for the header filename (IMemory_t -> IMemory)
                    base = node.struct_name[:-2] if node.struct_name.endswith("_t") else node.struct_name
                    if base not in seen_fps:
                        seen_fps[base] = node
        for base_name, fps_node in seen_fps.items():
            proto_header = self._emit_protocol_header(base_name, fps_node, ctxt)
            ctxt.output_files.append((f"{base_name}.h", proto_header))

        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, ir.DataTypeComponent):
                continue
            header = self._emit_header(type_name, dtype, ctxt, protocol_headers=set(seen_fps.keys()))
            source = self._emit_source(type_name, dtype, ctxt)
            abi_sidecar = self._emit_abi_sidecar(type_name, dtype, ctxt)
            ctxt.output_files.append((f"{type_name}.h", header))
            ctxt.output_files.append((f"{type_name}.c", source))
            ctxt.output_files.append((f"{type_name}_abi.py", abi_sidecar))
        return ctxt

    def _emit_protocol_header(self, base_name: str, fps: "SwFuncPtrStruct", ctxt: SwContext) -> str:
        """Emit a standalone ``<base_name>.h`` that defines the protocol struct."""
        w = _Writer()
        guard = f"_{base_name.upper()}_H"
        w.line(f"#ifndef {guard}")
        w.line(f"#define {guard}")
        w.blank()
        w.line("#include <stdint.h>")
        w.line("#include <stddef.h>")
        w.line('#include "zsp_timebase.h"')
        w.blank()
        self._emit_func_ptr_struct(fps, ctxt, w)
        w.blank()
        w.line(f"#endif /* {guard} */")
        return w.getvalue()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _emit_header(
        self, name: str, dtype: ir.DataTypeComponent, ctxt: SwContext,
        protocol_headers: set = None,
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

        # Include mutex header and element type headers for claim_pool fields
        has_claim_pool = any(m.kind == "claim_pool" for m in fmeta.values())
        if has_claim_pool:
            w.line("#include \"zsp_mutex.h\"")
            for field in dtype.fields:
                m = fmeta.get(field.name)
                if m and m.kind == "claim_pool" and m.elem_type_name:
                    w.line(f"#include \"{m.elem_type_name}.h\"")
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

        # Emit static inline contract check functions (check_requires /
        # check_ensures) for any action types that carry role constraints.
        self._emit_action_contract_funcs(name, ctxt, w)

        # Emit static inline C functions collected from @staticmethod members of
        # action types referenced by this component.
        self._emit_static_inline_funcs(name, ctxt, w)

        # Include or inline-emit SwFuncPtrStruct typedefs so other
        # translation units can include and use the port types.
        nodes = ctxt.sw_nodes.get(name, [])
        has_fps = any(isinstance(n, SwFuncPtrStruct) for n in nodes)
        if has_fps:
            w.line('#include "zsp_timebase.h"')
            w.blank()
        emitted_fps: set = set()
        for node in nodes:
            if isinstance(node, SwFuncPtrStruct):
                if node.struct_name in emitted_fps:
                    continue
                emitted_fps.add(node.struct_name)
                # If a shared protocol header was generated for this struct,
                # include it instead of re-defining it inline.
                base = node.struct_name[:-2] if node.struct_name.endswith("_t") else node.struct_name
                if protocol_headers is not None and base in protocol_headers:
                    w.line(f'#include "{base}.h"')
                    w.blank()
                else:
                    self._emit_func_ptr_struct(node, ctxt, w)
                    w.blank()

        # Forward-declare the struct typedef, then emit the full struct body
        # so that other .h files that include this one can embed the type by value.
        w.line(f"typedef struct {name}_s {name}_t;")
        w.blank()

        # Full struct definition (must be in header for sub-component embedding)
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
        w.line(f"ZUSPEC_API void {name}_halt({name}_t *self);")
        w.line(f"ZUSPEC_API void {name}_request_halt({name}_t *self);")
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

        # Method port binder declarations
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "method_port":
                w.line(
                    f"ZUSPEC_API void {name}_bind_{field.name}("
                    f"{name}_t *self, {m.comp_type} proto, void *impl);"
                )

        # Method export descriptor declarations (defined in the .c file)
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m and m.kind == "method_export":
                w.line(f"extern {m.comp_type} {name}_{field.name};")
        w.blank()
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

        # Process function declarations (promoted @process with params)
        for func in dtype.functions:
            if not getattr(func, "metadata", {}).get("sync_convertible"):
                continue
            if not getattr(func, "metadata", {}).get("is_process"):
                continue
            param_parts = []
            if func.args and func.args.args:
                for arg in func.args.args:
                    c_t = _c_type_from_annotation(arg.annotation, ctxt)
                    param_parts.append(f"{c_t} {arg.arg}")
            ret_type = "void" if func.returns is None else _c_type(func.returns, ctxt)
            if param_parts:
                params_str = ", ".join(param_parts)
                w.line(
                    f"ZUSPEC_API {ret_type} {name}_{func.name}({name}_t *self, {params_str});"
                )

        # Async process entry function declarations (promoted @process with params, non-sync)
        for node in ctxt.sw_nodes.get(name, []):
            if not isinstance(node, SwCoroutineFrame):
                continue
            if not node.process_params:
                continue
            comp_name = node.comp_type_name or name
            fn_name = node.func_name or f"{name}_run"
            param_ann = {arg.arg: getattr(arg, 'annotation', None) for arg in node.process_params}
            param_parts = [
                f"{_c_type_from_annotation(param_ann[arg.arg], ctxt)} {arg.arg}"
                for arg in node.process_params
            ]
            ret_type = "void" if node.return_dtype is None else _c_type(node.return_dtype, ctxt)
            params_str = ", ".join(param_parts)
            sep = ", " if params_str else ""
            w.line(f"ZUSPEC_API {ret_type} {fn_name}({comp_name}_t *self{sep}{params_str});")

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

        has_claim_pool = any(m.kind == "claim_pool" for m in fmeta.values())
        if has_claim_pool:
            w.line('#include "zsp_mutex.h"')
            w.blank()

        has_memory = any(m.kind == "memory" for m in fmeta.values())
        if has_memory:
            w.line('#include "zsp_memory.h"')
            w.line('#include "zsp_alloc.h"')
            w.line('#include "zsp_init_ctxt.h"')
            w.blank()

        # Emit extern declarations for any devirtualized call targets.
        # When a port call is statically resolved to a concrete implementation,
        # the generated code emits a direct call {TargetComp}__{slot}[_task]
        # instead of the indirect function-pointer.  The compiler must see a
        # prototype for these functions; they are declared here as extern.
        _devirt = getattr(ctxt, "devirtualized", {})
        _devirt_decls = {}  # fn_name → decl_str
        for (init_comp, init_port), conn in _devirt.items():
            if init_comp != name:
                continue
            proto = conn.protocol
            if proto is None:
                continue
            target = conn.target_component
            if not target:
                continue
            # Get precise Python-level type hints for the protocol (same logic as
            # _emit_func_ptr_struct) to produce accurate C parameter types.
            proto_hints: dict = {}
            if proto.py_type is not None:
                try:
                    proto_hints = _get_protocol_method_hints(proto.py_type)
                except Exception:
                    pass
            for method in proto.methods:
                slot = method.name
                is_async = getattr(method, "is_async", False)
                fn_name = f"{target}__{slot}" + ("_task" if is_async else "")
                if fn_name in _devirt_decls:
                    continue
                py_hints = proto_hints.get(slot, {})
                # Build C parameter list using the same helper as _emit_func_ptr_struct
                arg_parts = self._func_ptr_arg_types(method, ctxt, py_hints)
                params = ["void *impl"]
                if is_async:
                    params.append("struct zsp_thread_s *thread")
                    params.extend(arg_parts)
                    params.append("struct zsp_frame_s **ret_pp")
                    ret_c = "struct zsp_frame_s *"
                else:
                    params.extend(arg_parts)
                    ret_py = py_hints.get("return")
                    if ret_py is not None:
                        ret_c = _py_annotation_to_c(ret_py, ctxt)
                    else:
                        ret_c = _c_type(method.returns, ctxt)
                decl = f"extern {ret_c} {fn_name}({', '.join(params)});"
                _devirt_decls[fn_name] = decl
        if _devirt_decls:
            w.line("/* Forward declarations for devirtualized port implementations */")
            for decl in _devirt_decls.values():
                w.line(decl)
            w.blank()

        # Emit global export descriptor definitions for ProtocolExport fields.
        # Function pointers are left NULL; the user (or DramModel_bind_exports)
        # must install them before simulation starts.
        has_method_export = any(m.kind == "method_export" for m in fmeta.values())
        if has_method_export:
            for field in dtype.fields:
                m = fmeta.get(field.name)
                if m and m.kind == "method_export":
                    w.line(
                        f"/* Export descriptor for {field.name} — "
                        f"set function pointers before use */"
                    )
                    w.line(f"{m.comp_type} {name}_{field.name} = {{0}};")
            w.blank()
        has_coroutine = any(isinstance(n, SwCoroutineFrame) for n in nodes)
        if has_coroutine:
            w.line('#include "zsp_timebase.h"')
            w.blank()

        # Hide all symbols by default; only ZUSPEC_API functions are exported
        w.line("#pragma GCC visibility push(hidden)")
        w.blank()

        # (struct body and SwFuncPtrStruct typedefs are in the .h for sub-component
        # embedding compatibility and cross-TU port type sharing)

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
                if node.process_params:
                    self._emit_coroutine_entry_fn(node, ctxt, w)
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
                        if isinstance(vt, ir.DataTypeAction):
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

    def _emit_action_contract_funcs(self, comp_name: str, ctxt: SwContext, w) -> None:
        """Emit ``static inline`` contract-check functions for action types.

        For each action type that was typedef'd for *comp_name* and whose
        Python class has ``@constraint.requires`` or ``@constraint.ensures``
        methods, two functions are emitted:

        * ``static inline void {ActionName}_check_requires({ActionName}_t *self)``
        * ``static inline void {ActionName}_check_ensures({ActionName}_t *self)``

        Both functions are emitted only when the corresponding role has at
        least one constraint.  The Python class is resolved via
        ``ctxt.py_globals`` using the action type name.
        """
        try:
            from zuspec.be.sw.contract_emitter import ActionContractEmitter
        except ImportError:
            return  # contract_emitter not available — skip silently

        emitter = ActionContractEmitter(field_prefix="self->")
        emitted_actions: set = set()

        def _try_emit(action_type: "ir.DataTypeAction") -> None:
            aname = action_type.name
            if aname in emitted_actions:
                return
            py_cls = ctxt.py_globals.get(aname)
            if py_cls is None:
                return  # Python class not accessible in this compilation unit
            req_lines = emitter.emit_requires(py_cls)
            ens_lines = emitter.emit_ensures(py_cls)
            if not req_lines and not ens_lines:
                return
            emitted_actions.add(aname)
            if req_lines:
                w.line(f"static inline void {aname}_check_requires({aname}_t *self) {{")
                w.line("    (void)self;")
                for line in req_lines:
                    w.line(f"    {line}")
                w.line("}")
                w.blank()
            if ens_lines:
                w.line(f"static inline void {aname}_check_ensures({aname}_t *self) {{")
                w.line("    (void)self;")
                for line in ens_lines:
                    w.line(f"    {line}")
                w.line("}")
                w.blank()

        for node in ctxt.sw_nodes.get(comp_name, []):
            if hasattr(node, 'locals_struct'):
                for local_var in node.locals_struct:
                    vt = getattr(local_var, 'var_type', None)
                    if isinstance(vt, ir.DataTypeAction):
                        _try_emit(vt)
            if hasattr(node, 'continuations'):
                for cont in node.continuations:
                    for vt in _collect_action_type_hints(cont.stmts).values():
                        if isinstance(vt, ir.DataTypeAction):
                            _try_emit(vt)

        # Also scan all action types in type_m
        for tname, dtype in ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeAction):
                _try_emit(dtype)

    def _emit_static_inline_funcs(self, comp_name: str, ctxt: SwContext, w) -> None:
        """Emit ``static inline`` C functions for each ``@staticmethod`` collected
        from action types referenced by *comp_name*'s coroutine frames."""
        emitted_funcs: set = set()

        def _emit_action_statics(action_type: "ir.DataTypeAction") -> None:
            for func in getattr(action_type, "static_methods", []):
                if func.name in emitted_funcs:
                    continue
                emitted_funcs.add(func.name)
                self._emit_static_inline_func(func, ctxt, w)

        seen_actions: set = set()

        def _consider_action(action_type: "ir.DataTypeAction") -> None:
            if action_type.name not in seen_actions:
                seen_actions.add(action_type.name)
                _emit_action_statics(action_type)

        for node in ctxt.sw_nodes.get(comp_name, []):
            if hasattr(node, 'locals_struct'):
                for local_var in node.locals_struct:
                    vt = getattr(local_var, 'var_type', None)
                    if isinstance(vt, ir.DataTypeAction):
                        _consider_action(vt)
            if hasattr(node, 'continuations'):
                for cont in node.continuations:
                    for vt in _collect_action_type_hints(cont.stmts).values():
                        if isinstance(vt, ir.DataTypeAction):
                            _consider_action(vt)

        # Also scan all action types in type_m — they may be inlined without locals
        for tname, dtype in ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeAction):
                _consider_action(dtype)

    def _emit_static_inline_func(self, func: "ir.Function", ctxt: SwContext, w) -> None:
        """Emit a single ``static inline uint32_t name(...)`` function.

        Uses an ``#ifndef`` / ``#define`` / ``#endif`` idempotency guard so that
        the same helper (e.g. ``_sext``) can be included from multiple headers
        without triggering a redefinition error.
        """
        from zuspec.be.sw.stmt_generator import StmtGenerator

        guard = f"_ZSP_FUNC_{func.name.upper()}_DEFINED"
        w.line(f"#ifndef {guard}")
        w.line(f"#define {guard}")

        # Build parameter list — all parameters default to uint32_t.
        param_names = set()
        params = []
        if func.args:
            for arg in func.args.args:
                params.append(f"uint32_t {arg.arg}")
                param_names.add(arg.arg)
        params_str = ", ".join(params) if params else "void"

        w.line(f"static inline uint32_t {func.name}({params_str}) {{")
        w.indent()

        # Declare local variables (those that are assigned in the body but are
        # not parameters).
        body_stmts = func.body or []
        locals_needed = _collect_unresolved_names(body_stmts) - param_names
        for lname in sorted(locals_needed):
            w.line(f"uint32_t {lname};")

        sg = StmtGenerator(
            component=None,
            ctxt=ctxt,
            py_globals={},
            locals_struct_names=set(),
            tlm_port_mode=True,
        )
        for stmt in body_stmts:
            code = sg._gen_dm_stmt(stmt)
            if code.strip():
                for line in code.splitlines():
                    w.line(line)

        w.dedent()
        w.line("}")
        w.line("#endif")
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
            elif m.kind == "claim_pool":
                elem = m.elem_type_name or "void"
                w.line(f"{elem}_t {field.name};  /* ClaimPool<{elem}> */")
                w.line(f"zsp_mutex_t {field.name}_mutex;")
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
            elif m.kind in ("method_port", "method_export"):
                w.line(f"{m.comp_type} {field.name};  /* method {'port' if m.kind == 'method_port' else 'export'} */")
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
        w.line(f"volatile uint8_t _halt_requested;  /* safe async halt from callbacks */")
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
            elif m and m.kind == "claim_pool":
                elem = m.elem_type_name or "void"
                w.line(f"{elem}_init(&self->{field.name});")
                w.line(f"zsp_mutex_init(&self->{field.name}_mutex, 1);")
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
        w.line("self->_halt_requested = 0;")
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
        w.blank()
        w.line(f"ZUSPEC_API void {name}_halt({name}_t *self) {{")
        w.indent()
        w.line("longjmp(self->_halt_jmp, 1);")
        w.dedent()
        w.line("}")
        w.blank()
        w.line(f"ZUSPEC_API void {name}_request_halt({name}_t *self) {{")
        w.indent()
        w.line("self->_halt_requested = 1;")
        w.dedent()
        w.line("}")

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
        """Emit `bind_{port}` functions for each CallablePort and method port field."""
        for field in dtype.fields:
            m = fmeta.get(field.name)
            if m is None:
                continue
            if m.kind == "callable_port":
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
            elif m.kind == "method_port":
                w.line(
                    f"ZUSPEC_API void {name}_bind_{field.name}("
                    f"{name}_t *self, {m.comp_type} proto, void *impl) {{"
                )
                w.indent()
                w.line(f"self->{field.name} = proto;")
                w.line(f"self->{field.name}.impl = impl;")
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
        # _halt
        _fn(f"{name}_halt", [ptr], "None")
        # _request_halt (safe to call from ctypes callbacks — sets a flag)
        _fn(f"{name}_request_halt", [ptr], "None")

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
        sg = StmtGenerator(py_globals=ctxt.py_globals, tlm_port_mode=True)
        # Build parameter list from func.args
        param_names: set = set()
        param_parts = []
        if func.args and func.args.args:
            for arg in func.args.args:
                c_t = _c_type_from_annotation(arg.annotation, ctxt)
                param_parts.append(f"{c_t} {arg.arg}")
                param_names.add(arg.arg)

        ret_type = "void"
        if func.returns is not None:
            ret_type = _c_type(func.returns, ctxt)

        if param_parts:
            params_str = ", ".join(param_parts)
            sig = f"ZUSPEC_API {ret_type} {comp_name}_{func.name}({comp_name}_t *self, {params_str})"
        else:
            sig = f"static {ret_type} {comp_name}_{func.name}({comp_name}_t *self)"
        w.line(f"{sig} {{")
        w.indent()
        # Declare any local variables used in the body (excluding params)
        body = func.body if isinstance(func.body, list) else []
        locals_needed = _collect_unresolved_names(body) - param_names
        for lname in sorted(locals_needed):
            w.line(f"uint32_t {lname} = 0;")
        for stmt in body:
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
        # Build annotation map for process params
        param_ann = {}
        for arg in (frame.process_params or []):
            param_ann[arg.arg] = getattr(arg, 'annotation', None)
        w.line(f"typedef struct {{")
        w.indent()
        w.line("zsp_frame_t frame;")
        w.line(f"{comp_name}_t *self;")
        for lv in (frame.locals_struct or []):
            if lv.var_type is not None:
                c_t = _c_type(lv.var_type, ctxt)
            elif lv.var_name in param_ann:
                c_t = _c_type_from_annotation(param_ann[lv.var_name], ctxt)
            else:
                c_t = "int"
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

    def _emit_coroutine_entry_fn(
        self, frame: SwCoroutineFrame, ctxt: SwContext, w: _Writer
    ) -> None:
        """Emit a callable entry wrapper for a coroutine with process params.

        Drives all continuations in order.  For ``wait()``/suspend points the
        timebase fast-path is used (no other threads, no pending events), so
        time advances inline without requiring a real scheduler.  The return
        value of the last continuation is the function result.
        """
        fn_name = frame.func_name or "coroutine"
        comp_name = frame.comp_type_name or "Comp"
        param_ann = {arg.arg: getattr(arg, 'annotation', None) for arg in (frame.process_params or [])}
        param_parts = [
            f"{_c_type_from_annotation(param_ann[arg.arg], ctxt)} {arg.arg}"
            for arg in (frame.process_params or [])
        ]
        ret_type = "void"
        if frame.return_dtype is not None:
            ret_type = _c_type(frame.return_dtype, ctxt)
        params_str = ", ".join(param_parts)
        sep = ", " if params_str else ""
        n_conts = len(frame.continuations)

        w.line(f"ZUSPEC_API {ret_type} {fn_name}({comp_name}_t *self{sep}{params_str}) {{")
        w.indent()
        w.line(f"{fn_name}_locals_t locals = {{{{0}}}};")
        w.line("zsp_thread_t thread = {{0}};")
        w.line("zsp_timebase_t tb = {{0}};")
        w.line("locals.self = self;")
        for arg in (frame.process_params or []):
            w.line(f"locals.{arg.arg} = {arg.arg};")
        w.line("thread.leaf = (zsp_frame_t *)&locals;")
        w.line("thread.timebase = &tb;")
        if ret_type != "void":
            w.line("zsp_frame_t *_r = NULL;")
        for idx in range(n_conts):
            if ret_type != "void":
                w.line(f"_r = {fn_name}_task(&tb, &thread, {idx});")
            else:
                w.line(f"{fn_name}_task(&tb, &thread, {idx});")
        if ret_type != "void":
            w.line(f"return ({ret_type})(uintptr_t)_r;")
        w.dedent()
        w.line("}")

    def _emit_continuation(
        self, fn_name: str, cont: SwContinuation, ctxt: SwContext, w: _Writer,
        component=None,
        locals_struct_names=None,
    ) -> None:
        _lsn = set(locals_struct_names) if locals_struct_names else set()

        # Collect method_port fields on this component that can have their impl
        # pointer hoisted — port bindings are structurally immutable after init(),
        # so caching "self->port.impl" in a local variable is always safe and
        # eliminates one load instruction per port call inside the loop body.
        hoisted_ports: Set[str] = set()
        # Map port_field_name → SwConnection for statically-resolved ports.
        # Used by StmtGenerator to emit direct calls when callee names are known.
        devirt_map: dict = {}
        if component is not None:
            fmeta = _collect_field_meta(component, ctxt)
            hoisted_ports = {
                fname for fname, m in fmeta.items()
                if m.kind == "method_port"
            }
            # Query the devirtualization table built by DevirtualizePass
            _devirt = getattr(ctxt, "devirtualized", {})
            comp_type_name = component.name or ""
            for fname in hoisted_ports:
                conn = _devirt.get((comp_type_name, fname))
                if conn is not None:
                    devirt_map[fname] = conn

        sg = StmtGenerator(
            component=component,
            ctxt=ctxt,
            py_globals=ctxt.py_globals,
            locals_struct_names=_lsn,
            tlm_port_mode=True,
            hoisted_ports=hoisted_ports,
            devirt_map=devirt_map,
        )
        w.line(f"case {cont.index}: {{")
        w.indent()

        # Declare any unresolved local variable names, using the correct type.
        # Typed hints (DataTypeAction, DataTypeTupleReturn) get their C struct type;
        # names from zdc.uN() casts get the inferred integer type;
        # names used as '->field' pointer bases get _zsp_stub_t *;
        # all other vars fall back to uint32_t.
        #
        # Note: stub_ptr_names may include names excluded from unresolved (pure attr bases
        # like `claim` in `claim->t->execute(...)`) — declare those separately.
        type_hints = _collect_action_type_hints(cont.stmts)
        prim_hints = _infer_local_types_from_assigns(cont.stmts)
        stub_ptr_names = _collect_stub_ptr_names(cont.stmts)
        unresolved = _collect_unresolved_names(cont.stmts) - _lsn
        all_to_declare = unresolved | (stub_ptr_names - _lsn)
        for name in sorted(all_to_declare):
            if name in type_hints:
                c_t = _c_type(type_hints[name], ctxt)
                w.line(f"{c_t} {name} = {{{{0}}}};")
            elif name in prim_hints:
                w.line(f"{prim_hints[name]} {name} = 0;")
            elif name in stub_ptr_names:
                w.line(f"_zsp_stub_t *{name} = NULL;")
            else:
                w.line(f"uint32_t {name} = 0;")

        # Hoist port impl pointers: emit one cached local per method_port field.
        # The CPU must otherwise reload these through the self pointer on every
        # iteration because GCC cannot prove the indirect call doesn't alias self.
        for fname in sorted(hoisted_ports):
            w.line(f"void *_{fname}_impl = self->{fname}.impl;")

        for stmt in cont.stmts:
            code = sg._gen_dm_stmt(stmt)
            if code.strip():
                for line in code.splitlines():
                    w.line(line)
        if cont.suspend is not None:
            self._emit_suspend_point(cont.suspend, cont.next_index, w, ctxt=ctxt)
        else:
            w.line("/* coroutine complete */")
            w.line("return NULL;")
        w.dedent()
        w.line("}")

    def _emit_suspend_point(
        self, sp: SwSuspendPoint, next_idx: Optional[int], w: _Writer,
        ctxt: Optional[SwContext] = None,
    ) -> None:
        if isinstance(sp, SwSuspendWait):
            dur = sp.duration_expr
            tlm_mode = getattr(ctxt, "tlm_sync_mode", "") if ctxt is not None else ""
            if tlm_mode:
                # TLM / LT mode: use ZSP_WAIT_PS so both precise and LT compilation
                # work from the same generated C (controlled by -DZSP_LT_MODE).
                ps_expr = _duration_to_ps_str(dur)
                w.line(f"ZSP_WAIT_PS(thread, {ps_expr});")
            else:
                # Legacy precise-mode path: use zsp_timebase_wait with ZSP_TIME_S.
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
        elif isinstance(sp, SwSuspendCompletion):
            # ZDC_COMPLETION_AWAIT(c, out, size, frame, label)
            field = sp.completion_field or "completion"
            out_var = sp.out_var or "result"
            elem_type = _c_type(sp.elem_type, ctxt) if sp.elem_type and ctxt else "uint32_t"
            size_expr = f"sizeof({elem_type})"
            w.line(
                f"ZDC_COMPLETION_AWAIT(&self->{field}, &{out_var}, {size_expr}, "
                f"frame, _label_{next_idx if next_idx is not None else 'end'});"
            )
        elif isinstance(sp, SwSuspendSpawn):
            # zdc_spawn() is non-blocking; just emit the call then fall through.
            fn_name = sp.spawned_func or "unknown_fn"
            arg_expr = sp.arg_expr
            handle = sp.handle_var or "_spawn_handle"
            arg_str = "NULL"
            if arg_expr is not None:
                from zuspec.be.sw.stmt_generator import StmtGenerator
                try:
                    sg = StmtGenerator(ctxt)
                    arg_str = sg.emit_expr(arg_expr)
                except Exception:
                    arg_str = "NULL"
            w.line(
                f"zdc_spawn(&{handle}, {fn_name}, {arg_str}, "
                f"_spawn_stack_{handle}, sizeof(_spawn_stack_{handle}));"
            )
            # Not a real suspension; fall through without break
            return
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

    def _emit_func_ptr_struct(self, fps: SwFuncPtrStruct, ctxt: SwContext, w: _Writer) -> None:
        # Build Python type-hint map for the Protocol class (if available)
        # so we can emit precise C types even when the IR loses annotation detail.
        proto_hints: Optional[Dict[str, Any]] = None
        if fps.protocol_type is not None and fps.protocol_type.py_type is not None:
            try:
                proto_hints = _get_protocol_method_hints(fps.protocol_type.py_type)
            except Exception:
                proto_hints = None

        w.line(f"typedef struct {{")
        w.indent()
        w.line("void *impl;")
        for slot in fps.slots:
            sig = slot.signature  # ir.Function or None
            py_hints = (proto_hints or {}).get(slot.slot_name)
            if sig is not None and sig.is_async:
                # Async method: coroutine task signature
                arg_parts = self._func_ptr_arg_types(sig, ctxt, py_hints)
                args_str = ", ".join(arg_parts)
                sep = ", " if args_str else ""
                w.line(
                    f"struct zsp_frame_s *(*{slot.slot_name})"
                    f"(void *impl, struct zsp_thread_s *thread"
                    f"{sep}{args_str}, struct zsp_frame_s **ret_pp);"
                )
            elif sig is not None and not sig.is_async:
                # Sync method: plain function pointer
                ret_py = (py_hints or {}).get("return")
                if ret_py is not None:
                    ret_c = _py_annotation_to_c(ret_py, ctxt)
                else:
                    ret_c = _c_type_from_annotation(getattr(sig, "returns", None), ctxt)
                arg_parts = self._func_ptr_arg_types(sig, ctxt, py_hints)
                args_str = ", ".join(arg_parts)
                sep = ", " if args_str else ""
                w.line(f"{ret_c} (*{slot.slot_name})(void *impl{sep}{args_str});")
            else:
                # No signature info — emit a generic slot
                w.line(f"void (*{slot.slot_name})(void *);")
        w.dedent()
        w.line(f"}} {fps.struct_name};")

    def _func_ptr_arg_types(
        self, sig: Any, ctxt: SwContext, py_hints: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Return a list of C ``type name`` strings for non-self arguments of *sig*."""
        if sig is None or sig.args is None:
            return []
        parts = []
        for arg in sig.args.args:
            if arg.arg == "self":
                continue
            # Prefer Python type hint (more accurate for Protocol methods)
            py_t = (py_hints or {}).get(arg.arg)
            if py_t is not None:
                c_type = _py_annotation_to_c(py_t, ctxt)
            else:
                c_type = _c_type_from_annotation(arg.annotation, ctxt)
            parts.append(f"{c_type} {arg.arg}")
        return parts

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

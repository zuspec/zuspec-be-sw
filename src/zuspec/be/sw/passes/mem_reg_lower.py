"""MemRegAccessLowerPass — lower register and memory API calls to SW IR nodes.

Two modes:
- ``mode="iss"``  → register reads/writes become ``SwRegRead`` / ``SwRegWrite``
  targeting direct C struct field accesses on an in-memory register model.
- ``mode="bfm"``  → register reads/writes become ``SwRegRead`` / ``SwRegWrite``
  flagged for BFM indirect access (``bfm_reg_read`` / ``bfm_reg_write`` calls).

Pattern matching
----------------
* Calls to ``DataTypeRegister`` instance methods ``read()`` / ``read_val()`` →
  ``SwRegRead``
* Calls to ``DataTypeRegister`` instance methods ``write()`` / ``write_val()`` →
  ``SwRegWrite``
* Calls to ``DataTypeAddressSpace`` read/write helpers → ``SwMemRead`` /
  ``SwMemWrite`` (width inferred from the call's keyword / positional args if
  present).

The matched call nodes are recorded as ``SwRegRead`` / ``SwRegWrite`` /
``SwMemRead`` / ``SwMemWrite`` in ``ctxt.sw_nodes[comp_name]``.  The original
function bodies are **not** mutated (a follow-up CEmit phase can query the
sw_nodes to decide how to emit each call).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.memory import SwMemRead, SwMemWrite, SwRegRead, SwRegWrite
from zuspec.be.sw.pipeline import SwPass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REG_READ_METHODS: Set[str] = {"read", "read_val"}
_REG_WRITE_METHODS: Set[str] = {"write", "write_val"}
_MEM_READ_METHODS: Set[str] = {"read8", "read16", "read32", "read64", "read"}
_MEM_WRITE_METHODS: Set[str] = {"write8", "write16", "write32", "write64", "write"}

_WIDTH_FROM_SUFFIX: Dict[str, int] = {"8": 8, "16": 16, "32": 32, "64": 64}


def _method_name(call: ir.ExprCall) -> Optional[str]:
    """Return the method name if *call* is an attribute call, else None."""
    if isinstance(call.func, ir.ExprAttribute):
        return call.func.attr
    return None


def _receiver(call: ir.ExprCall) -> Optional[ir.Expr]:
    """Return the receiver expression of an attribute call."""
    if isinstance(call.func, ir.ExprAttribute):
        return call.func.value
    return None


def _receiver_type(recv: ir.Expr, ctxt: SwContext) -> Optional[ir.DataType]:
    """Best-effort: resolve the DataType of the receiver expression."""
    if recv is None:
        return None
    if isinstance(recv, ir.ExprAttribute):
        # self.reg_field → look up field type in context
        owner = recv.value
        if isinstance(owner, ir.TypeExprRefSelf):
            # Walk all component types looking for the field
            for dtype in ctxt.type_m.values():
                if isinstance(dtype, ir.DataTypeComponent):
                    for field in dtype.fields:
                        if field.name == recv.attr:
                            return _resolve(field.datatype, ctxt)
    return None


def _resolve(dtype: ir.DataType, ctxt: SwContext) -> ir.DataType:
    if isinstance(dtype, ir.DataTypeRef):
        resolved = ctxt.type_m.get(dtype.ref_name)
        return resolved if resolved else dtype
    return dtype


def _width_from_method(method_name: str) -> int:
    """Infer access width in bits from method suffix (read32 → 32)."""
    for suffix, w in _WIDTH_FROM_SUFFIX.items():
        if method_name.endswith(suffix):
            return w
    return 32


def _collect_calls(stmts: list, calls: List[ir.ExprCall]) -> None:
    """Recursively collect all ExprCall nodes from *stmts*."""
    for stmt in stmts:
        _collect_calls_node(stmt, calls)


def _collect_calls_node(node, calls: List[ir.ExprCall]) -> None:
    if isinstance(node, ir.ExprCall):
        calls.append(node)
    if not hasattr(node, "__dataclass_fields__"):
        return
    for fname in node.__dataclass_fields__:
        val = getattr(node, fname, None)
        if isinstance(val, (ir.Stmt, ir.Expr)):
            _collect_calls_node(val, calls)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, (ir.Stmt, ir.Expr)):
                    _collect_calls_node(item, calls)


# ---------------------------------------------------------------------------
# MemRegAccessLowerPass
# ---------------------------------------------------------------------------

class MemRegAccessLowerPass(SwPass):
    """Lower register and memory API calls to ``SwRegRead`` / ``SwRegWrite`` /
    ``SwMemRead`` / ``SwMemWrite`` nodes.

    Arguments
    ----------
    mode:
        ``"iss"`` (default) — target direct in-memory struct access.
        ``"bfm"``           — target BFM function-pointer indirect access.

    Example::

        pass_ = MemRegAccessLowerPass(mode="iss")
        sw_ctxt = pass_.run(sw_ctxt)
    """

    def __init__(self, mode: str = "iss") -> None:
        if mode not in ("iss", "bfm"):
            raise ValueError(f"Unknown mode {mode!r}; expected 'iss' or 'bfm'")
        self.mode = mode

    def run(self, ctxt: SwContext) -> SwContext:
        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, (ir.DataTypeComponent, ir.DataTypeClass)):
                continue
            for func in getattr(dtype, "functions", []):
                self._lower_function(func, type_name, ctxt)
        return ctxt

    def _lower_function(
        self, func: ir.Function, comp_name: str, ctxt: SwContext
    ) -> None:
        calls: List[ir.ExprCall] = []
        _collect_calls(func.body, calls)

        for call in calls:
            method = _method_name(call)
            if method is None:
                continue
            recv = _receiver(call)
            recv_type = _receiver_type(recv, ctxt)

            if isinstance(recv_type, ir.DataTypeRegister):
                self._lower_reg_call(call, method, recv, comp_name, ctxt)
            elif isinstance(recv_type, ir.DataTypeAddressSpace):
                self._lower_mem_call(call, method, recv, comp_name, ctxt)
            elif method in _REG_READ_METHODS:
                # Type not resolved — record on method-name match
                self._lower_reg_call(call, method, recv, comp_name, ctxt)
            elif method in _REG_WRITE_METHODS:
                self._lower_reg_call(call, method, recv, comp_name, ctxt)
            elif method in (_MEM_READ_METHODS | _MEM_WRITE_METHODS) and method not in (
                _REG_READ_METHODS | _REG_WRITE_METHODS
            ):
                self._lower_mem_call(call, method, recv, comp_name, ctxt)

    def _lower_reg_call(
        self,
        call: ir.ExprCall,
        method: str,
        recv: Optional[ir.Expr],
        comp_name: str,
        ctxt: SwContext,
    ) -> None:
        if method in _REG_READ_METHODS:
            node = SwRegRead(
                reg_expr=recv,
                field_name=_attr_name(recv),
                mode=self.mode,
            )
        else:
            val = call.args[0] if call.args else None
            node = SwRegWrite(
                reg_expr=recv,
                field_name=_attr_name(recv),
                value_expr=val,
                mode=self.mode,
            )
        ctxt.sw_nodes.setdefault(comp_name, []).append(node)

    def _lower_mem_call(
        self,
        call: ir.ExprCall,
        method: str,
        recv: Optional[ir.Expr],
        comp_name: str,
        ctxt: SwContext,
    ) -> None:
        width = _width_from_method(method)
        addr = call.args[0] if call.args else None

        if method in _MEM_READ_METHODS:
            node = SwMemRead(
                addr_expr=addr,
                width=width,
                signed=False,
                mode=self.mode,
            )
        else:
            val = call.args[1] if len(call.args) > 1 else None
            node = SwMemWrite(
                addr_expr=addr,
                width=width,
                value_expr=val,
                mode=self.mode,
            )
        ctxt.sw_nodes.setdefault(comp_name, []).append(node)


def _attr_name(expr: Optional[ir.Expr]) -> Optional[str]:
    if isinstance(expr, ir.ExprAttribute):
        return expr.attr
    return None

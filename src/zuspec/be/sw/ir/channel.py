"""SW IR channel/port nodes: FIFOs, function-pointer structs, export bindings."""
from __future__ import annotations

import dataclasses as dc
from typing import List, Optional, Any

from zuspec.dataclasses import ir
from .base import SwNode


@dc.dataclass(kw_only=True)
class SwFifo(SwNode):
    """A software FIFO (channel) declaration.

    Attributes
    ----------
    field_name:
        Name of the component field that holds this channel.
    element_type:
        ``DataType`` of each element.
    depth:
        Maximum number of elements.
    """
    field_name: Optional[str] = dc.field(default=None)
    element_type: Optional[ir.DataType] = dc.field(default=None)
    depth: int = dc.field(default=16)


@dc.dataclass(kw_only=True)
class SwFifoPush(SwNode):
    """Push one element onto a ``SwFifo``."""
    fifo_ref: Optional[SwFifo] = dc.field(default=None)
    value_expr: Optional[ir.Expr] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwFifoPop(SwNode):
    """Pop one element from a ``SwFifo``.

    Attributes
    ----------
    out_var:
        Name of the local variable that receives the popped value.
    """
    fifo_ref: Optional[SwFifo] = dc.field(default=None)
    out_var: Optional[str] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwFuncSlot(SwNode):
    """One slot in a ``SwFuncPtrStruct`` (maps to one method of a protocol).

    Attributes
    ----------
    slot_name:
        C identifier for the function pointer field.
    signature:
        The IR ``Function`` whose signature this slot mirrors.
    """
    slot_name: Optional[str] = dc.field(default=None)
    signature: Optional[Any] = dc.field(default=None)  # ir.Function


@dc.dataclass(kw_only=True)
class SwFuncPtrStruct(SwNode):
    """A C struct of function pointers representing a protocol or callable port.

    Attributes
    ----------
    struct_name:
        C typedef name for this struct (e.g. ``MemIface_t``).
    slots:
        One ``SwFuncSlot`` per protocol method or callable.
    protocol_type:
        The ``ir.DataTypeProtocol`` this struct was built from, if any.
        Used to look up original Python type hints for precise C types.
    """
    struct_name: Optional[str] = dc.field(default=None)
    slots: List[SwFuncSlot] = dc.field(default_factory=list)
    protocol_type: Optional[Any] = dc.field(default=None)  # ir.DataTypeProtocol


@dc.dataclass(kw_only=True)
class SwExportBind(SwNode):
    """Binding from a ``SwFuncPtrStruct`` slot to a concrete function.

    Attributes
    ----------
    struct_ref:
        The ``SwFuncPtrStruct`` whose slot is being wired.
    slot_name:
        Name of the slot being bound.
    target_comp_path:
        Dot-separated instance path of the component that implements the
        function.
    target_func_name:
        Name of the concrete function on the target component.
    """
    struct_ref: Optional[SwFuncPtrStruct] = dc.field(default=None)
    slot_name: Optional[str] = dc.field(default=None)
    target_comp_path: Optional[str] = dc.field(default=None)
    target_func_name: Optional[str] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwDirectCall(SwNode):
    """A devirtualized method-port call — direct function call to a known export.

    Produced by ``DevirtualizePass`` when a port call site can be resolved to a
    single concrete target at compile time (because the binding graph is static).

    Attributes
    ----------
    callee_component:
        Type name of the concrete component that owns the implementation
        (e.g. ``"DRAMModel"``).
    callee_method:
        Coroutine task function name on the callee (e.g. ``"DRAMModel_transport_task"``).
    callee_impl_expr:
        C expression that evaluates to the ``impl`` (``void *``) pointer at the
        call site (e.g. ``"self->bank0"``).
    args:
        List of C expressions for additional method arguments.
    """
    callee_component: str = dc.field(default="")
    callee_method: str = dc.field(default="")
    callee_impl_expr: str = dc.field(default="")
    args: List[str] = dc.field(default_factory=list)

"""SW IR coroutine nodes: frames, continuations, and suspend-point subtypes."""
from __future__ import annotations

import dataclasses as dc
from typing import List, Optional, Any

from zuspec.dataclasses import ir
from .base import SwNode


@dc.dataclass(kw_only=True)
class SwLocalVar(SwNode):
    """A local variable that must survive across a suspend point.

    Attributes
    ----------
    var_name:
        C identifier for this variable.
    var_type:
        ``DataType`` of the variable.
    """
    var_name: Optional[str] = dc.field(default=None)
    var_type: Optional[ir.DataType] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwSuspendPoint(SwNode):
    """Abstract base for all suspend points inside a coroutine continuation."""


@dc.dataclass(kw_only=True)
class SwSuspendWait(SwSuspendPoint):
    """Suspend for a time duration (``wait(n)`` or ``delay(n)``)."""
    duration_expr: Optional[ir.Expr] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwSuspendCall(SwSuspendPoint):
    """Suspend until a general async call returns."""
    call_expr: Optional[ir.Expr] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwSuspendFifoPop(SwSuspendPoint):
    """Suspend until a value is available in a FIFO (``channel.get()``)."""
    fifo_field: Optional[str] = dc.field(default=None)
    out_var: Optional[str] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwSuspendFifoPush(SwSuspendPoint):
    """Suspend until a FIFO has space (``channel.put(v)``)."""
    fifo_field: Optional[str] = dc.field(default=None)
    value_expr: Optional[ir.Expr] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwSuspendMutex(SwSuspendPoint):
    """Suspend until a ``ClaimPool`` mutex is acquired."""
    pool_field: Optional[str] = dc.field(default=None)
    out_var: Optional[str] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwContinuation(SwNode):
    """A single continuation within a coroutine (code between two suspend points).

    Attributes
    ----------
    index:
        Numeric index used as the switch-case label.
    stmts:
        Statements executed in this continuation.
    suspend:
        The ``SwSuspendPoint`` at the end of this continuation (``None`` for
        the final continuation).
    next_index:
        Switch-case label to jump to after the suspend point resolves.
    """
    index: int = dc.field(default=0)
    stmts: List[Any] = dc.field(default_factory=list)  # ir.Stmt
    suspend: Optional[SwSuspendPoint] = dc.field(default=None)
    next_index: Optional[int] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwCoroutineFrame(SwNode):
    """A coroutine state machine for one async function.

    Attributes
    ----------
    func_name:
        C identifier for the generated coroutine function.
    comp_type_name:
        Name of the owning component type.
    locals_struct:
        Variables that live across at least one suspend point and must be
        stored in the frame struct.
    continuations:
        Ordered list of ``SwContinuation`` objects representing the switch
        arms.
    process_params:
        For ``@process`` methods with parameters, the list of ``(name, Arg)``
        tuples.  These are added to the locals struct and an entry function
        that accepts them is emitted.
    return_dtype:
        Optional return ``DataType`` for entry functions that return a value.
    """
    func_name: Optional[str] = dc.field(default=None)
    comp_type_name: Optional[str] = dc.field(default=None)
    locals_struct: List[SwLocalVar] = dc.field(default_factory=list)
    continuations: List[SwContinuation] = dc.field(default_factory=list)
    process_params: List[Any] = dc.field(default_factory=list)  # List of (name, annotation_expr)
    return_dtype: Optional[Any] = dc.field(default=None)  # DataType or None

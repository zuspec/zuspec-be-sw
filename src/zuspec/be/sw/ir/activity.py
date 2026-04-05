"""SW IR activity nodes: schedulers, action execution, seq/par/select blocks."""
from __future__ import annotations

import dataclasses as dc
from typing import List, Optional, Any

from zuspec.dataclasses import ir
from .base import SwNode


@dc.dataclass(kw_only=True)
class SwSchedulerNode(SwNode):
    """Root scheduling node for one ``DataTypeClass`` (Action).

    Attributes
    ----------
    action_type:
        The ``DataTypeClass`` this scheduler drives.
    root:
        The top-level ``SwSeqBlock`` (or ``SwParBlock``) that describes the
        full execution order.
    """
    action_type: Optional[ir.DataTypeClass] = dc.field(default=None)
    root: Optional["SwSeqBlock"] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwActionExec(SwNode):
    """Execute a single child action.

    Attributes
    ----------
    action_type:
        The ``DataTypeClass`` of the action being executed.
    handle_name:
        Local handle name (``self.<name>`` in the source).  ``None`` for
        anonymous traversals.
    solve_constraints:
        Inline constraint expressions collected from ``ActivityConstraint``
        nodes enclosing this exec.
    """
    action_type: Optional[ir.DataTypeClass] = dc.field(default=None)
    handle_name: Optional[str] = dc.field(default=None)
    solve_constraints: List[ir.Expr] = dc.field(default_factory=list)


@dc.dataclass(kw_only=True)
class SwSeqBlock(SwNode):
    """Execute children sequentially."""
    children: List[SwNode] = dc.field(default_factory=list)


@dc.dataclass(kw_only=True)
class SwParBlock(SwNode):
    """Execute children in parallel.

    Attributes
    ----------
    join:
        ``"all"`` — wait for all branches.
        ``"first"`` — wait for the first branch to complete.
        ``"none"`` — fire-and-forget.
        ``"select"`` — select exactly one branch (used for *replicate*).
    """
    children: List[SwNode] = dc.field(default_factory=list)
    join: str = dc.field(default="all")


@dc.dataclass(kw_only=True)
class SwSelectBranch(SwNode):
    """One branch of a ``SwSelectNode``.

    Attributes
    ----------
    weight:
        Optional expression giving this branch's random weight.
    guard:
        Optional boolean guard that must be true for the branch to be
        eligible.
    body:
        The ``SwSeqBlock`` (or other ``SwNode``) executed when this branch
        is chosen.
    """
    weight: Optional[ir.Expr] = dc.field(default=None)
    guard: Optional[ir.Expr] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwSelectNode(SwNode):
    """Non-deterministically select and execute one branch."""
    branches: List[SwSelectBranch] = dc.field(default_factory=list)

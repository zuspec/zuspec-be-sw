"""SW IR resource nodes: mutex acquire/release and indexed-pool selection."""
from __future__ import annotations

import dataclasses as dc
from typing import List, Optional, Any

from zuspec.dataclasses import ir
from .base import SwNode


@dc.dataclass(kw_only=True)
class SwMutexAcquire(SwNode):
    """Acquire a ``ClaimPool`` mutex.

    Attributes
    ----------
    pool_expr:
        Expression resolving to the ``ClaimPool`` field.
    out_var:
        Name of the local variable that receives the acquired unit handle.
    body:
        Statements to execute while the mutex is held.  The corresponding
        ``SwMutexRelease`` is emitted after this block.
    """
    pool_expr: Optional[ir.Expr] = dc.field(default=None)
    out_var: Optional[str] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwMutexRelease(SwNode):
    """Release a ``ClaimPool`` mutex.

    Attributes
    ----------
    pool_expr:
        Expression resolving to the same ``ClaimPool`` field as the
        corresponding ``SwMutexAcquire``.
    acquire_ref:
        Back-reference to the paired ``SwMutexAcquire`` node.
    """
    pool_expr: Optional[ir.Expr] = dc.field(default=None)
    acquire_ref: Optional[SwMutexAcquire] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class SwIndexedSelect(SwNode):
    """Acquire and later release a slot from an ``IndexedPool``.

    Attributes
    ----------
    pool_expr:
        Expression resolving to the ``IndexedPool`` field.
    index_var:
        Name of the local variable that receives the acquired index.
    """
    pool_expr: Optional[ir.Expr] = dc.field(default=None)
    index_var: Optional[str] = dc.field(default=None)

"""SW IR memory nodes: register and memory read/write operations."""
from __future__ import annotations

import dataclasses as dc
from typing import Optional

from zuspec.dataclasses import ir
from .base import SwNode


@dc.dataclass(kw_only=True)
class SwRegRead(SwNode):
    """Read a hardware register field."""
    reg_expr: Optional[ir.Expr] = dc.field(default=None)
    field_name: Optional[str] = dc.field(default=None)
    out_var: Optional[str] = dc.field(default=None)
    mode: str = dc.field(default="iss")


@dc.dataclass(kw_only=True)
class SwRegWrite(SwNode):
    """Write a hardware register field."""
    reg_expr: Optional[ir.Expr] = dc.field(default=None)
    field_name: Optional[str] = dc.field(default=None)
    value_expr: Optional[ir.Expr] = dc.field(default=None)
    mode: str = dc.field(default="iss")


@dc.dataclass(kw_only=True)
class SwMemRead(SwNode):
    """Read from an address space (memory).

    Attributes
    ----------
    addr_expr:
        Expression for the byte address.
    width:
        Read width in bits (8, 16, 32, or 64).
    signed:
        Whether the result should be sign-extended.
    out_var:
        Local variable that receives the result.
    mode:
        ``"iss"`` or ``"bfm"``
    """
    addr_expr: Optional[ir.Expr] = dc.field(default=None)
    width: int = dc.field(default=32)
    signed: bool = dc.field(default=False)
    out_var: Optional[str] = dc.field(default=None)
    mode: str = dc.field(default="iss")


@dc.dataclass(kw_only=True)
class SwMemWrite(SwNode):
    """Write to an address space (memory).

    Attributes
    ----------
    addr_expr:
        Expression for the byte address.
    width:
        Write width in bits (8, 16, 32, or 64).
    value_expr:
        Expression producing the value to write.
    mode:
        ``"iss"`` or ``"bfm"``
    """
    addr_expr: Optional[ir.Expr] = dc.field(default=None)
    width: int = dc.field(default=32)
    value_expr: Optional[ir.Expr] = dc.field(default=None)
    mode: str = dc.field(default="iss")

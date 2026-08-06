"""SW IR memory nodes: register and memory read/write operations."""
from __future__ import annotations

import dataclasses as dc
from typing import Optional

import zuspec.ir.core as ir
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
class SwRegRmw(SwNode):
    """Read-modify-write one hardware register -- PSS 3.1 §21.14.1::

        REG_VAL(new) = (REG_VAL(current) & ~mask) | (val & mask)

    ONE NODE, not an ``SwRegRead`` followed by an ``SwRegWrite``. The pair was
    the obvious encoding and it loses the two things that matter: ``sw_nodes``
    is a flat per-type list with no ordering against the statements it came
    from, so nothing downstream could tell that a particular read and a
    particular write are the same operation on the same register -- or that
    they may not be separated, reordered, or have the read elided.

    That last point is not hypothetical. The masked write's read is part of the
    LRM's definition, and on a register whose read has side effects -- a channel
    CSR that clears its status and interrupt-source bits -- dropping it changes
    device behaviour. A consumer that saw a bare ``SwRegRead`` whose result is
    never named would be right, on the face of it, to drop it.

    ``mask_expr`` and ``value_expr`` arrive already folded to constants wherever
    the source allowed: the compiler reduces ``write_field`` / ``write_fields``
    / ``write_masked`` to this one form, so no field name reaches here.
    """
    reg_expr: Optional[ir.Expr] = dc.field(default=None)
    field_name: Optional[str] = dc.field(default=None)
    mask_expr: Optional[ir.Expr] = dc.field(default=None)
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

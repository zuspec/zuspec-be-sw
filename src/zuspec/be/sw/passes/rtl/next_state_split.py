"""
NextStateSplitPass — identify all fields written inside @sync bodies.

For every field written in a @sync process, its name is added to
``ctx.rtl_nxt_fields``.  Downstream (CEmitPass) uses this set to:
  1. Add a ``<field>_nxt`` member to the generated struct.
  2. Rewrite write references to ``self-><field>_nxt`` in the sync body.
  3. Emit the ``Foo_advance()`` function that copies _nxt → current.

Read references are always to the *current* field; only write targets
(left-hand sides of StmtAssign / StmtAugAssign) in @sync bodies get _nxt.
"""
from __future__ import annotations

from zuspec.dataclasses.ir.expr import ExprRefField, TypeExprRefSelf, ExprAttribute
from zuspec.dataclasses.ir.stmt import (
    Stmt, StmtAssign, StmtAugAssign, StmtIf, StmtFor, StmtWhile,
)

from zuspec.be.sw.ir.base import SwContext


def _target_field_index(tgt) -> int:
    """Return the component field index written by *tgt*, or -1 if unrecognized."""
    if isinstance(tgt, ExprRefField) and isinstance(tgt.base, TypeExprRefSelf):
        return tgt.index
    # Bundle/struct attribute write: self.io.valid → bundle field self.io
    if isinstance(tgt, ExprAttribute):
        val = tgt.value
        if isinstance(val, ExprRefField) and isinstance(val.base, TypeExprRefSelf):
            return val.index
    return -1


def _collect_written_fields(stmts: list, written: set) -> None:
    """Recursively collect field indices written in *stmts*."""
    for stmt in stmts:
        if isinstance(stmt, StmtAssign):
            for tgt in stmt.targets:
                idx = _target_field_index(tgt)
                if idx >= 0:
                    written.add(idx)
        elif isinstance(stmt, StmtAugAssign):
            idx = _target_field_index(stmt.target)
            if idx >= 0:
                written.add(idx)
        # Descend into control-flow bodies
        for attr in ("body", "orelse", "handlers", "finalbody"):
            sub = getattr(stmt, attr, None)
            if sub and isinstance(sub, list):
                _collect_written_fields(sub, written)


class NextStateSplitPass:
    """Populate ``ctx.rtl_nxt_fields`` with names of @sync-written fields."""

    def run(self, ctx: SwContext) -> SwContext:
        comp = ctx.rtl_component
        fields = comp.fields

        written_indices: set = set()
        for fn in comp.sync_processes:
            _collect_written_fields(fn.body, written_indices)

        ctx.rtl_nxt_fields = {fields[i].name for i in written_indices if i < len(fields)}
        return ctx

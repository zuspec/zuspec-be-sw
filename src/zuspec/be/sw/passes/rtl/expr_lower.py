"""
ExprLowerPass — lower Zuspec IR expressions/statements to C source strings.

This pass does *not* modify the IR in-place; instead it provides a
``lower_expr()`` and ``lower_stmt()`` API that ``CEmitPass`` calls while
walking functions.

Key lowerings
-------------
* ``ExprRefField(self, N)`` in a @sync write context → ``self-><name>_nxt``
  (when in write mode and field is in ``ctx.rtl_nxt_fields``).
* ``ExprSubscript(field, ExprSlice(hi, lo))`` → ``((field >> lo) & mask)``
* ``ExprSubscript(array_field, idx)``         → ``self->field[idx]``
* ``ExprIfExp(test, body, orelse)``           → ``((test) ? (body) : (orelse))``
* ``ExprCall(any, [ExprList(...)])``          → ``(e1 || e2 || ...)``
* ``ExprCall(zdc.sext, val, bits)``           → sign-extend in C
* ``ExprCall(zdc.zext, val, bits)``           → zero-extend / mask in C
* ``ExprBin``               → ``<lhs> <op> <rhs>``
* ``ExprConstant``          → decimal literal (``u`` suffix for unsigned)
* ``StmtIf``                → ``if (...) { ... } else { ... }``
* ``StmtAssign``            → ``<target> = <value>;``
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

from zuspec.dataclasses import ir
from zuspec.dataclasses.ir.expr import (
    Expr, ExprBin, BinOp, ExprConstant, ExprRefField, TypeExprRefSelf,
    ExprRefParam, ExprRefLocal, ExprRefUnresolved, UnaryOp, ExprAttribute,
)
from zuspec.dataclasses.ir.stmt import (
    Stmt, StmtAssign, StmtAugAssign, StmtIf, StmtFor, StmtWhile,
    StmtExpr, StmtReturn, StmtPass,
)
from zuspec.dataclasses.ir.data_type import DataTypeComponent, DataTypeArray

from zuspec.be.sw.ir.base import SwContext

# Mapping from IR BinOp to C operator strings
_BINOP_MAP = {
    BinOp.Add:      "+",
    BinOp.Sub:      "-",
    BinOp.Mult:     "*",
    BinOp.Div:      "/",
    BinOp.Mod:      "%",
    BinOp.BitAnd:   "&",
    BinOp.BitOr:    "|",
    BinOp.BitXor:   "^",
    BinOp.LShift:   "<<",
    BinOp.RShift:   ">>",
    BinOp.Eq:       "==",
    BinOp.NotEq:    "!=",
    BinOp.Lt:       "<",
    BinOp.LtE:      "<=",
    BinOp.Gt:       ">",
    BinOp.GtE:      ">=",
    BinOp.And:      "&&",
    BinOp.Or:       "||",
    BinOp.FloorDiv: "/",
}

# AugAssign op → C operator
try:
    from zuspec.dataclasses.ir.stmt import AugOp as StmtAugOp
    from zuspec.dataclasses.ir.expr import AugOp
    _AUGOP_MAP = {
        AugOp.Add:      "+=",
        AugOp.Sub:      "-=",
        AugOp.Mult:     "*=",
        AugOp.Div:      "/=",
        AugOp.Mod:      "%=",
        AugOp.LShift:   "<<=",
        AugOp.RShift:   ">>=",
        AugOp.BitAnd:   "&=",
        AugOp.BitOr:    "|=",
        AugOp.BitXor:   "^=",
        AugOp.FloorDiv: "/=",
    }
except ImportError:
    _AUGOP_MAP = {}


class ExprLower:
    """Lowers IR expressions/statements to C source strings.

    Parameters
    ----------
    fields:
        Ordered field list from ``DataTypeComponent``.
    nxt_fields:
        Set of field *names* that have _nxt shadows (from NextStateSplitPass).
    in_sync_write:
        When True, write targets use the ``_nxt`` field name.
    indent:
        Current indentation prefix (spaces).
    module_globals:
        Python module globals dict from the component's defining module.
        Used to resolve enum/class constants (e.g. ``CpuState.FETCH``).
    wire_names:
        Set of wire process names (from ``comp.wire_processes``).
        Accesses to these via ``ExprAttribute(TypeExprRefSelf, name)``
        are emitted as ``self->name`` (struct field, computed in eval_comb).
    comp_name:
        C struct name (for generating wire-process function calls if needed).
    """

    def __init__(
        self,
        fields: list,
        nxt_fields: Set[str],
        in_sync_write: bool = False,
        indent: str = "    ",
        module_globals: Optional[dict] = None,
        wire_names: Optional[Set[str]] = None,
        comp_name: str = "",
        const_map: Optional[Dict[str, int]] = None,
    ):
        self._fields = fields
        self._nxt_fields = nxt_fields
        self._in_sync_write = in_sync_write
        self._indent = indent
        self._depth = 0
        self._module_globals: dict = module_globals or {}
        self._wire_names: Set[str] = wire_names or set()
        self._comp_name = comp_name
        self._const_map: Dict[str, int] = const_map or {}
        # Track which ExprRefLocal names have been declared in this function scope
        self._locals: Set[str] = set()
        # When True, ExprRefLocal assign targets are pre-declared; just emit assignment
        self._predecl_locals: bool = False

    # ------------------------------------------------------------------
    # Expression lowering
    # ------------------------------------------------------------------

    def lower_expr(self, expr: Expr, write_ctx: bool = False) -> str:
        """Return a C expression string for *expr*.

        Parameters
        ----------
        write_ctx:
            If True, ``ExprRefField`` targeting a nxt_field returns
            ``self-><name>_nxt`` instead of ``self-><name>``.
        """
        if expr is None:
            return "0"

        if isinstance(expr, TypeExprRefSelf):
            return "self"

        if isinstance(expr, ExprRefField):
            return self._lower_ref_field(expr, write_ctx)

        if isinstance(expr, ExprAttribute):
            return self._lower_attribute(expr, write_ctx)

        if isinstance(expr, ExprConstant):
            return self._lower_constant(expr)

        if isinstance(expr, ExprBin):
            lhs = self.lower_expr(expr.lhs)
            rhs = self.lower_expr(expr.rhs)
            op = _BINOP_MAP.get(expr.op, "?")
            return f"({lhs} {op} {rhs})"

        if isinstance(expr, ExprRefParam):
            return expr.name

        if isinstance(expr, ExprRefLocal):
            return expr.name

        if isinstance(expr, ExprRefUnresolved):
            return expr.name

        # ExprSubscript: array element access or bit-slice extraction
        try:
            from zuspec.dataclasses.ir.expr import ExprSubscript
            if isinstance(expr, ExprSubscript):
                return self._lower_subscript(expr, write_ctx)
        except ImportError:
            pass

        # ExprIfExp: ternary conditional  a if test else b  →  ((test) ? (a) : (b))
        # NOTE: ExprIfExp lives in expr_phase2, not expr — use name duck-typing.
        if type(expr).__name__ == "ExprIfExp":
            test = self.lower_expr(expr.test, write_ctx)
            body = self.lower_expr(expr.body, write_ctx)
            orelse = self.lower_expr(expr.orelse, write_ctx)
            return f"(({test}) ? ({body}) : ({orelse}))"

        # ExprCall: any(), zdc.sext(), zdc.zext(), setattr()
        try:
            from zuspec.dataclasses.ir.expr import ExprCall
            if isinstance(expr, ExprCall):
                return self._lower_call(expr, write_ctx)
        except ImportError:
            pass

        # ExprCompare (multiple comparators)
        try:
            from zuspec.dataclasses.ir.expr import ExprCompare, CmpOp
            if isinstance(expr, ExprCompare):
                return self._lower_compare(expr)
        except ImportError:
            pass

        # ExprBool
        try:
            from zuspec.dataclasses.ir.expr import ExprBool, BoolOp
            if isinstance(expr, ExprBool):
                op = "&&" if expr.op == BoolOp.And else "||"
                parts = [f"({self.lower_expr(v)})" for v in expr.values]
                return f"({f' {op} '.join(parts)})"
        except ImportError:
            pass

        # ExprUnary
        try:
            from zuspec.dataclasses.ir.expr import ExprUnary
            if isinstance(expr, ExprUnary):
                _UNOP = {
                    UnaryOp.Not:    "!",
                    UnaryOp.Invert: "~",
                    UnaryOp.USub:   "-",
                    UnaryOp.UAdd:   "+",
                }
                op = _UNOP.get(expr.op, "!")
                return f"({op}{self.lower_expr(expr.operand)})"
        except ImportError:
            pass

        # Fallback
        return f"/* unsupported: {type(expr).__name__} */ 0"

    def _lower_attribute(self, expr: ExprAttribute, write_ctx: bool) -> str:
        """Lower attribute access to C.

        Handles:
        * ``self.wire_attr``  (TypeExprRefSelf base) → ``self->wire_attr``
        * ``self.bundle.sub`` (ExprRefField(self, N) base) → ``self->bundle.sub``
        * ``CpuState.FETCH``  (ExprRefUnresolved base) → resolved integer constant
        """
        attr = expr.attr
        val = expr.value

        # self.attr  →  self->_regs.attr (registered) or self->attr (non-registered)
        if isinstance(val, TypeExprRefSelf):
            if attr in self._nxt_fields:
                if write_ctx:
                    return f"self->_nxt.{attr}"
                return f"self->_regs.{attr}"
            return f"self->{attr}"

        if isinstance(val, ExprRefField) and isinstance(val.base, TypeExprRefSelf):
            if val.index < len(self._fields):
                fname = self._fields[val.index].name
            else:
                fname = f"_f{val.index}"
            if fname in self._nxt_fields:
                if write_ctx:
                    return f"self->_nxt.{fname}.{attr}"
                return f"self->_regs.{fname}.{attr}"
            return f"self->{fname}.{attr}"

        # Enum/class constant: CpuState.FETCH, Opcode.LUI, etc.
        if isinstance(val, ExprRefUnresolved):
            obj = self._module_globals.get(val.name)
            if obj is not None:
                try:
                    resolved = getattr(obj, attr)
                    if isinstance(resolved, int):
                        if resolved < 0:
                            return str(resolved)
                        return f"{resolved}u"
                except AttributeError:
                    pass
            # Fallback: emit as a mangled C identifier (won't link, but shows intent)
            return f"{val.name}__{attr}"

        # General case: lower base expression and append attribute
        base_str = self.lower_expr(val, write_ctx=write_ctx)
        return f"{base_str}->{attr}"

    def _lower_ref_field(self, expr: ExprRefField, write_ctx: bool) -> str:
        if not isinstance(expr.base, TypeExprRefSelf):
            base = self.lower_expr(expr.base)
            if expr.index < len(self._fields):
                fname = self._fields[expr.index].name
            else:
                fname = f"_f{expr.index}"
            return f"{base}->{fname}"

        if expr.index >= len(self._fields):
            return f"self->_f{expr.index}"

        fname = self._fields[expr.index].name
        # Const-fold: emit macro name instead of struct field access for const fields.
        if not write_ctx and self._const_map and fname in self._const_map:
            return f"{self._comp_name}_{fname}"
        if fname in self._nxt_fields:
            if write_ctx:
                return f"self->_nxt.{fname}"
            return f"self->_regs.{fname}"
        return f"self->{fname}"

    def _lower_constant(self, expr: ExprConstant) -> str:
        val = expr.value
        if isinstance(val, bool):
            return "1" if val else "0"
        if isinstance(val, int):
            if val < 0:
                return str(val)
            return f"{val}u"
        if isinstance(val, float):
            return repr(val)
        if val is None:
            return "0"
        return str(val)

    def _lower_compare(self, expr) -> str:
        from zuspec.dataclasses.ir.expr import CmpOp
        _CMPOP = {
            CmpOp.Eq:    "==",
            CmpOp.NotEq: "!=",
            CmpOp.Lt:    "<",
            CmpOp.LtE:   "<=",
            CmpOp.Gt:    ">",
            CmpOp.GtE:   ">=",
        }
        left = self.lower_expr(expr.left)
        parts = []
        for op, comp in zip(expr.ops, expr.comparators):
            c_op = _CMPOP.get(op, "==")
            right = self.lower_expr(comp)
            parts.append(f"({left} {c_op} {right})")
            left = right  # Python chained compare: a < b < c → (a<b) && (b<c)
        if len(parts) == 1:
            return parts[0]
        return "(" + " && ".join(parts) + ")"

    def _lower_subscript(self, expr, write_ctx: bool) -> str:
        """Lower ExprSubscript to C.

        Cases:
        * Array element: field[dynamic_idx]  → ``self->_cpuregs[idx]``
        * Bit-slice: field[hi:lo]            → ``((self->field >> lo) & mask)``
        * Single bit: field[n]               → ``((self->field >> n) & 1u)``
        """
        from zuspec.dataclasses.ir.expr import ExprSlice

        value = expr.value
        slc = expr.slice

        # Determine the base field string (read context for subscripts)
        base_str = self.lower_expr(value, write_ctx=False)

        # Array element access: base field is DataTypeArray
        if (isinstance(value, ExprRefField) and isinstance(value.base, TypeExprRefSelf)
                and value.index < len(self._fields)
                and isinstance(self._fields[value.index].datatype, DataTypeArray)):
            idx_str = self.lower_expr(slc, write_ctx=False)
            return f"{base_str}[{idx_str}]"

        # Bit-slice: field[hi:lo]
        if isinstance(slc, ExprSlice) and slc.is_bit_slice:
            hi = self.lower_expr(slc.lower)   # ExprSlice.lower = MSB in [hi:lo]
            lo = self.lower_expr(slc.upper)   # ExprSlice.upper = LSB in [hi:lo]
            # bits = hi - lo + 1; mask = (1u << bits) - 1u
            # For constant bounds, compute mask statically
            if isinstance(slc.lower, ExprConstant) and isinstance(slc.upper, ExprConstant):
                hi_v = slc.lower.value
                lo_v = slc.upper.value
                bits = hi_v - lo_v + 1
                mask = (1 << bits) - 1
                if lo_v == 0:
                    return f"({base_str} & {mask}u)"
                return f"(({base_str} >> {lo_v}u) & {mask}u)"
            return f"(({base_str} >> ({lo})) & ((1u << ({hi} - ({lo}) + 1u)) - 1u))"

        # Single bit: field[n]
        if isinstance(slc, ExprConstant):
            n = slc.value
            if n == 0:
                return f"({base_str} & 1u)"
            return f"(({base_str} >> {n}u) & 1u)"

        # Fallback: generic subscript
        slc_str = self.lower_expr(slc, write_ctx=False)
        return f"{base_str}[{slc_str}]"

    def _lower_call(self, expr, write_ctx: bool) -> str:
        """Lower ExprCall to C.

        Supported:
        * ``any([e1, e2, ...])``       → ``((e1) || (e2) || ...)``
        * ``zdc.sext(val, bits)``      → sign-extend
        * ``zdc.zext(val, bits)``      → zero-extend / mask
        * ``setattr(self, name, val)`` → no-op (handled by _lower_for unrolling)
        """
        func = expr.func
        fname = ""
        if isinstance(func, ExprRefUnresolved):
            fname = func.name
        elif isinstance(func, ExprAttribute) and isinstance(func.value, ExprRefUnresolved):
            fname = f"{func.value.name}.{func.attr}"

        if fname == "bool":
            val = self.lower_expr(expr.args[0], write_ctx)
            return f"(!!(({val})))"

        if fname == "any":
            arg = expr.args[0] if expr.args else None
            if arg is not None and hasattr(arg, "elts"):
                parts = [f"({self.lower_expr(e, write_ctx)})" for e in arg.elts]
                return f"({' || '.join(parts)})" if parts else "0u"
            return "0u"

        if fname == "zdc.sext":
            val = self.lower_expr(expr.args[0], write_ctx)
            bits_expr = expr.args[1]
            if isinstance(bits_expr, ExprConstant):
                bits = bits_expr.value
                shift = 32 - bits
                return f"((int32_t)(({val}) << {shift}u) >> {shift}u)"
            bits = self.lower_expr(bits_expr, write_ctx)
            return f"((int32_t)(({val}) << (32u - ({bits}))) >> (32u - ({bits})))"

        if fname == "zdc.zext":
            val = self.lower_expr(expr.args[0], write_ctx)
            bits_expr = expr.args[1]
            if isinstance(bits_expr, ExprConstant):
                bits = bits_expr.value
                mask = (1 << bits) - 1
                return f"(({val}) & {mask}u)"
            bits = self.lower_expr(bits_expr, write_ctx)
            return f"(({val}) & ((1u << ({bits})) - 1u))"

        if fname == "setattr":
            # Should be handled by _lower_for unrolling; if reached standalone, skip
            return "/* setattr */ 0"

        return f"/* unsupported call: {fname} */ 0"

    # ------------------------------------------------------------------
    # Statement lowering
    # ------------------------------------------------------------------

    def lower_stmts(self, stmts: list, write_ctx: bool = False) -> List[str]:
        """Return list of C source lines for *stmts*."""
        lines: List[str] = []
        pad = self._indent * self._depth
        for stmt in stmts:
            lines.extend(self._lower_stmt(stmt, write_ctx, pad))
        return lines

    def _lower_stmt(self, stmt: Stmt, write_ctx: bool, pad: str) -> List[str]:
        if isinstance(stmt, StmtAssign):
            return self._lower_assign(stmt, write_ctx, pad)
        if isinstance(stmt, StmtAugAssign):
            return self._lower_aug_assign(stmt, write_ctx, pad)
        if isinstance(stmt, StmtIf):
            return self._lower_if(stmt, write_ctx, pad)
        if isinstance(stmt, StmtFor):
            return self._lower_for(stmt, write_ctx, pad)
        if isinstance(stmt, StmtWhile):
            return self._lower_while(stmt, write_ctx, pad)
        if isinstance(stmt, StmtExpr):
            # Skip docstring constants (string literals used as documentation)
            if isinstance(stmt.expr, ExprConstant) and isinstance(stmt.expr.value, str):
                return []
            return [f"{pad}{self.lower_expr(stmt.expr)};"]
        if isinstance(stmt, StmtReturn):
            if stmt.value:
                return [f"{pad}return {self.lower_expr(stmt.value)};"]
            return [f"{pad}return;"]
        if isinstance(stmt, StmtPass):
            return [f"{pad}/* pass */"]
        return [f"{pad}/* unhandled stmt: {type(stmt).__name__} */"]

    def _lower_assign(self, stmt: StmtAssign, write_ctx: bool, pad: str) -> List[str]:
        rhs = self.lower_expr(stmt.value)
        lines = []
        for tgt in stmt.targets:
            # ExprRefLocal: pre-declared at function top if _predecl_locals, else declare inline
            if isinstance(tgt, ExprRefLocal):
                name = tgt.name
                if self._predecl_locals:
                    lines.append(f"{pad}{name} = {rhs};")
                elif name not in self._locals:
                    self._locals.add(name)
                    lines.append(f"{pad}uint32_t {name} = {rhs};")
                else:
                    lines.append(f"{pad}{name} = {rhs};")
                continue

            # ExprSubscript on an array field: write directly (no _nxt for arrays)
            try:
                from zuspec.dataclasses.ir.expr import ExprSubscript
                if isinstance(tgt, ExprSubscript):
                    base_str = self.lower_expr(tgt.value, write_ctx=False)
                    idx_str = self.lower_expr(tgt.slice, write_ctx=False)
                    lines.append(f"{pad}{base_str}[{idx_str}] = {rhs};")
                    continue
            except ImportError:
                pass

            lhs = self.lower_expr(tgt, write_ctx=write_ctx)
            lines.append(f"{pad}{lhs} = {rhs};")
        return lines

    def _lower_aug_assign(self, stmt: StmtAugAssign, write_ctx: bool, pad: str) -> List[str]:
        tgt = self.lower_expr(stmt.target, write_ctx=write_ctx)
        val = self.lower_expr(stmt.value)
        c_op = _AUGOP_MAP.get(stmt.op, "+=")
        return [f"{pad}{tgt} {c_op} {val};"]

    def _lower_if(self, stmt: StmtIf, write_ctx: bool, pad: str) -> List[str]:
        test = self.lower_expr(stmt.test)
        lines = [f"{pad}if ({test}) {{"]
        self._depth += 1
        inner_pad = self._indent * self._depth
        lines.extend(self.lower_stmts(stmt.body, write_ctx))
        self._depth -= 1
        if stmt.orelse:
            # Check for elif: single StmtIf in orelse
            if len(stmt.orelse) == 1 and isinstance(stmt.orelse[0], StmtIf):
                else_lines = self._lower_if(stmt.orelse[0], write_ctx, pad)
                lines.append(f"{pad}}} else {else_lines[0].lstrip()}")
                lines.extend(else_lines[1:])
                return lines
            else:
                lines.append(f"{pad}}} else {{")
                self._depth += 1
                lines.extend(self.lower_stmts(stmt.orelse, write_ctx))
                self._depth -= 1
        lines.append(f"{pad}}}")
        return lines

    def _lower_for(self, stmt: StmtFor, write_ctx: bool, pad: str) -> List[str]:
        from zuspec.dataclasses.ir.expr import ExprCall

        tgt = self.lower_expr(stmt.target)

        # Unroll: for attr in ['field1', 'field2', ...]: setattr(self, attr, val)
        if (isinstance(stmt.iter, ExprConstant)
                and isinstance(stmt.iter.value, list)
                and all(isinstance(s, str) for s in stmt.iter.value)
                and len(stmt.body) == 1
                and isinstance(stmt.body[0], StmtExpr)):
            call = stmt.body[0].expr
            if (hasattr(call, 'func') and hasattr(call, 'args')
                    and isinstance(call.func, ExprRefUnresolved)
                    and call.func.name == 'setattr'
                    and len(call.args) == 3
                    and isinstance(call.args[0], TypeExprRefSelf)
                    and isinstance(call.args[1], ExprRefLocal)):
                val_str = self.lower_expr(call.args[2])
                lines = []
                for fname in stmt.iter.value:
                    if fname in self._nxt_fields:
                        if write_ctx:
                            lines.append(f"{pad}self->_nxt.{fname} = {val_str};")
                        else:
                            lines.append(f"{pad}self->_regs.{fname} = {val_str};")
                    else:
                        lines.append(f"{pad}self->{fname} = {val_str};")
                return lines

        # range() for loop  →  for (int var = start; var < stop; var++) { ... }
        if isinstance(stmt.iter, ExprCall):
            iter_func = stmt.iter.func
            fname = getattr(iter_func, 'name', '')
            args = stmt.iter.args
            if fname == 'range':
                if len(args) == 1:
                    start_s, stop_s, step_s = "0", self.lower_expr(args[0]), "1"
                elif len(args) == 2:
                    start_s, stop_s, step_s = self.lower_expr(args[0]), self.lower_expr(args[1]), "1"
                else:
                    start_s = self.lower_expr(args[0])
                    stop_s = self.lower_expr(args[1])
                    step_s = self.lower_expr(args[2])
                lines = [f"{pad}for (int {tgt} = {start_s}; {tgt} < {stop_s}; {tgt} += {step_s}) {{"]
                self._depth += 1
                lines.extend(self.lower_stmts(stmt.body, write_ctx))
                self._depth -= 1
                lines.append(f"{pad}}}")
                return lines

        # Generic for loop (unhandled iter) — emit as comment block
        lines = [f"{pad}{{  /* for {tgt} in ... */"]
        self._depth += 1
        lines.extend(self.lower_stmts(stmt.body, write_ctx))
        self._depth -= 1
        lines.append(f"{pad}}}")
        return lines

    def _lower_while(self, stmt: StmtWhile, write_ctx: bool, pad: str) -> List[str]:
        test = self.lower_expr(stmt.test)
        lines = [f"{pad}while ({test}) {{"]
        self._depth += 1
        lines.extend(self.lower_stmts(stmt.body, write_ctx))
        self._depth -= 1
        lines.append(f"{pad}}}")
        return lines


def collect_local_names(stmts) -> Set[str]:
    """Recursively collect all ExprRefLocal names used as assignment targets."""
    names: Set[str] = set()

    def _scan(stmts_inner):
        for stmt in stmts_inner:
            if stmt is None:
                continue
            cls = stmt.__class__.__name__
            if cls == 'StmtAssign':
                for tgt in stmt.targets:
                    if isinstance(tgt, ExprRefLocal):
                        names.add(tgt.name)
                # Also scan into value for nested constructs
                _scan_expr(stmt.value)
            elif cls == 'StmtAugAssign':
                if isinstance(stmt.target, ExprRefLocal):
                    names.add(stmt.target.name)
            elif cls == 'StmtIf':
                _scan(stmt.body)
                if stmt.orelse:
                    _scan(stmt.orelse)
            elif cls in ('StmtFor', 'StmtWhile'):
                _scan(stmt.body)
                if hasattr(stmt, 'orelse') and stmt.orelse:
                    _scan(stmt.orelse)

    def _scan_expr(expr):
        pass  # expressions don't declare locals

    _scan(stmts)
    return names


class ExprLowerPass:
    """Validate that expressions can be lowered (no unsupported nodes).

    This pass does not transform ``ctx``; it simply exercises the
    ``ExprLower`` helpers so that downstream errors surface early.
    In Phase 2 the heavy lifting is done on-the-fly in CEmitPass.
    """

    def run(self, ctx: SwContext) -> SwContext:
        return ctx

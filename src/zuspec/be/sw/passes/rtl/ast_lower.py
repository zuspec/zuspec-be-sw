"""
ASTLower — lower Python AST stage bodies to C source strings.

Pipeline stages (@zdc.stage) are recorded as raw Python ASTs (body_ast).
This module walks those ASTs and generates C code equivalent to the
sequential execution of all stages.
"""
from __future__ import annotations

import ast
from typing import Dict, List, Optional, Set


_BINOP_MAP = {
    ast.Add:      "+",
    ast.Sub:      "-",
    ast.Mult:     "*",
    ast.Div:      "/",
    ast.Mod:      "%",
    ast.BitAnd:   "&",
    ast.BitOr:    "|",
    ast.BitXor:   "^",
    ast.LShift:   "<<",
    ast.RShift:   ">>",
    ast.FloorDiv: "/",
}

_CMPOP_MAP = {
    ast.Eq:    "==",
    ast.NotEq: "!=",
    ast.Lt:    "<",
    ast.LtE:   "<=",
    ast.Gt:    ">",
    ast.GtE:   ">=",
}

_BOOLOP_MAP = {
    ast.And: "&&",
    ast.Or:  "||",
}

_UNARYOP_MAP = {
    ast.Not:    "!",
    ast.Invert: "~",
    ast.USub:   "-",
    ast.UAdd:   "+",
}


class ASTLower:
    """Walk a Python AST function body and emit C source lines.

    Parameters
    ----------
    fields_by_name:
        Mapping of field name → IR field object from the component.
    nxt_fields:
        Mutable set of field names with _nxt shadows.  This object is
        *updated* as writes are discovered during lowering.
    module_globals:
        The ``__globals__`` dict of the original Python function, used to
        resolve names like ``ACCUM_MAX`` to compile-time constants.
    type_mapper:
        ``TypeMapper`` instance (used to look up C types for new locals).
    """

    def __init__(
        self,
        fields_by_name: dict,
        nxt_fields: Set[str],
        module_globals: dict,
        type_mapper,
    ):
        self._fields = fields_by_name
        self._nxt_fields = nxt_fields
        self._globals = module_globals
        self._tm = type_mapper
        self._locals: Dict[str, str] = {}  # name → C type for declared locals

    def lower_function(
        self,
        fn_node: ast.FunctionDef,
        output_vars: List[str],
        indent: str = "    ",
    ) -> List[str]:
        """Lower a stage function body to C lines.

        Return-statement values are assigned to ``output_vars`` in order
        instead of generating a ``return`` statement.

        Parameters
        ----------
        fn_node:
            The ``ast.FunctionDef`` node for the stage.
        output_vars:
            Names of C variables to receive the return-tuple elements.
        indent:
            Indentation prefix for generated lines.
        """
        lines: List[str] = []
        for stmt in fn_node.body:
            lines.extend(self._lower_stmt(stmt, output_vars, indent, depth=0))
        return lines

    # ------------------------------------------------------------------ stmts

    def _lower_stmt(
        self, node: ast.stmt, output_vars, indent: str, depth: int
    ) -> List[str]:
        pad = indent * (depth + 1)
        if isinstance(node, ast.Expr):
            # Expression statements (e.g. docstrings) — skip
            return []
        if isinstance(node, ast.Assign):
            return self._lower_assign(node, output_vars, indent, depth)
        if isinstance(node, ast.AugAssign):
            return self._lower_aug_assign(node, indent, depth)
        if isinstance(node, ast.If):
            return self._lower_if(node, output_vars, indent, depth)
        if isinstance(node, ast.Return):
            return self._lower_return(node, output_vars, pad)
        return [f"{pad}/* unhandled AST stmt: {type(node).__name__} */"]

    def _lower_assign(self, node: ast.Assign, output_vars, indent, depth) -> List[str]:
        pad = indent * (depth + 1)
        rhs = self._lower_expr(node.value, write_ctx=False)
        lines = []
        for tgt in node.targets:
            lhs, c_type = self._lower_lhs(tgt)
            if lhs.startswith("self->"):
                lines.append(f"{pad}{lhs} = {rhs};")
            else:
                # New local variable — declare it
                if lhs not in self._locals:
                    c_type = c_type or "uint64_t"
                    self._locals[lhs] = c_type
                    lines.append(f"{pad}{c_type} {lhs} = {rhs};")
                else:
                    lines.append(f"{pad}{lhs} = {rhs};")
        return lines

    def _lower_aug_assign(self, node: ast.AugAssign, indent, depth) -> List[str]:
        pad = indent * (depth + 1)
        lhs, _ = self._lower_lhs(node.target)
        rhs = self._lower_expr(node.value, write_ctx=False)
        op = _BINOP_MAP.get(type(node.op), "+=".rstrip("="))
        return [f"{pad}{lhs} {op}= {rhs};"]

    def _lower_if(self, node: ast.If, output_vars, indent, depth) -> List[str]:
        pad = indent * (depth + 1)
        test = self._lower_expr(node.test)
        lines = [f"{pad}if ({test}) {{"]
        for stmt in node.body:
            lines.extend(self._lower_stmt(stmt, output_vars, indent, depth + 1))
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                else_lines = self._lower_if(node.orelse[0], output_vars, indent, depth)
                # Merge "} else if" 
                lines.append(f"{pad}}} else {else_lines[0].lstrip()}")
                lines.extend(else_lines[1:])
                return lines
            lines.append(f"{pad}}} else {{")
            for stmt in node.orelse:
                lines.extend(self._lower_stmt(stmt, output_vars, indent, depth + 1))
        lines.append(f"{pad}}}")
        return lines

    def _lower_return(self, node: ast.Return, output_vars: List[str], pad: str) -> List[str]:
        if not node.value or not output_vars:
            return []
        lines = []
        if isinstance(node.value, ast.Tuple):
            for var, elt in zip(output_vars, node.value.elts):
                lines.append(f"{pad}{var} = {self._lower_expr(elt)};")
        else:
            if output_vars:
                lines.append(f"{pad}{output_vars[0]} = {self._lower_expr(node.value)};")
        return lines

    # ------------------------------------------------------------------ exprs

    def _lower_expr(self, node: ast.expr, write_ctx: bool = False) -> str:
        if isinstance(node, ast.Constant):
            val = node.value
            if isinstance(val, bool):
                return "1" if val else "0"
            if isinstance(val, int):
                if val < 0:
                    return str(val)
                return f"{val}u"
            return repr(val)

        if isinstance(node, ast.Name):
            name = node.id
            # Resolve module-level constants
            if name in self._globals and isinstance(self._globals[name], int):
                v = self._globals[name]
                return f"{v}u" if v >= 0 else str(v)
            return name

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                attr = node.attr
                field = self._fields.get(attr)
                if field is not None:
                    if write_ctx and attr in self._nxt_fields:
                        return f"self->{attr}_nxt"
                    return f"self->{attr}"
                return f"self->{attr}"
            base = self._lower_expr(node.value)
            return f"{base}.{node.attr}"

        if isinstance(node, ast.BinOp):
            lhs = self._lower_expr(node.left)
            rhs = self._lower_expr(node.right)
            op = _BINOP_MAP.get(type(node.op), "+")
            return f"({lhs} {op} {rhs})"

        if isinstance(node, ast.UnaryOp):
            operand = self._lower_expr(node.operand)
            op = _UNARYOP_MAP.get(type(node.op), "!")
            return f"({op}{operand})"

        if isinstance(node, ast.BoolOp):
            op = _BOOLOP_MAP.get(type(node.op), "&&")
            parts = [f"({self._lower_expr(v)})" for v in node.values]
            return f"({f' {op} '.join(parts)})"

        if isinstance(node, ast.Compare):
            left = self._lower_expr(node.left)
            parts = []
            for op, comp in zip(node.ops, node.comparators):
                c_op = _CMPOP_MAP.get(type(op), "==")
                right = self._lower_expr(comp)
                parts.append(f"({left} {c_op} {right})")
                left = right
            if len(parts) == 1:
                return parts[0]
            return "(" + " && ".join(parts) + ")"

        if isinstance(node, ast.Tuple):
            # Should not appear in expression context outside return
            return "/* tuple */"

        if isinstance(node, ast.Call):
            # Best-effort: lower function name + args
            func = self._lower_expr(node.func)
            args = ", ".join(self._lower_expr(a) for a in node.args)
            return f"{func}({args})"

        return f"/* unsupported AST expr: {type(node).__name__} */"

    # ------------------------------------------------------------------ helpers

    def _lower_lhs(self, node: ast.expr):
        """Lower a left-hand-side node; return (c_lhs, optional_c_type)."""
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                attr = node.attr
                # Mark field as nxt
                self._nxt_fields.add(attr)
                return f"self->{attr}_nxt", None
            base = self._lower_expr(node.value)
            return f"{base}.{node.attr}", None
        if isinstance(node, ast.Name):
            return node.id, None
        return "/* unknown lhs */", None

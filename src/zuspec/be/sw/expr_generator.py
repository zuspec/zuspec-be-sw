#****************************************************************************
# Copyright 2019-2025 Matthew Ballance and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#****************************************************************************
"""
Expression code generation for converting datamodel expressions to C code.
"""
import ast
from typing import List, Optional


class ExprGenerator:
    """Generates C code from Python AST expressions."""

    def generate(self, expr: ast.expr) -> str:
        """Generate C code for an expression."""
        if isinstance(expr, ast.Call):
            return self._gen_call(expr)
        elif isinstance(expr, ast.Constant):
            return self._gen_constant(expr)
        elif isinstance(expr, ast.Name):
            return self._gen_name(expr)
        elif isinstance(expr, ast.BinOp):
            return self._gen_binop(expr)
        elif isinstance(expr, ast.Compare):
            return self._gen_compare(expr)
        elif isinstance(expr, ast.Attribute):
            return self._gen_attribute(expr)
        elif isinstance(expr, ast.UnaryOp):
            return self._gen_unaryop(expr)
        elif isinstance(expr, ast.Subscript):
            return self._gen_subscript(expr)
        else:
            return f"/* unsupported expr: {type(expr).__name__} */"

    def _gen_call(self, expr: ast.Call) -> str:
        """Generate C code for a function call."""
        func_name = self._get_func_name(expr.func)
        args = [self.generate(arg) for arg in expr.args]

        # Handle special builtins
        if func_name == "print":
            return self._gen_print_call(args)
        elif func_name == "range":
            # Range is handled specially in for loops
            return f"range({', '.join(args)})"
        else:
            return f"{func_name}({', '.join(args)})"

    def _get_func_name(self, func: ast.expr) -> str:
        """Extract function name from call expression."""
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            value = self.generate(func.value)
            return f"{value}->{func.attr}"
        return "unknown_func"

    def _gen_print_call(self, args: List[str]) -> str:
        """Generate C printf call from print arguments."""
        if not args:
            return 'fprintf(stdout, "\\n")'
        
        # For now, assume single string argument
        # Format string needs to be extracted and newline added
        arg = args[0]
        if arg.startswith('"') and arg.endswith('"'):
            # String literal - add newline
            format_str = arg[:-1] + '\\n"'
            return f"fprintf(stdout, {format_str})"
        else:
            # Variable - use %s format
            return f'fprintf(stdout, "%s\\n", {arg})'

    def _gen_constant(self, expr: ast.Constant) -> str:
        """Generate C code for a constant value."""
        if isinstance(expr.value, str):
            # Escape the string for C
            escaped = expr.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'"{escaped}"'
        elif isinstance(expr.value, bool):
            return "1" if expr.value else "0"
        elif isinstance(expr.value, (int, float)):
            return str(expr.value)
        elif expr.value is None:
            return "NULL"
        return str(expr.value)

    def _gen_name(self, expr: ast.Name) -> str:
        """Generate C code for a name reference."""
        # Map Python builtins to C equivalents
        name_map = {
            "True": "1",
            "False": "0",
            "None": "NULL",
        }
        return name_map.get(expr.id, expr.id)

    def _gen_binop(self, expr: ast.BinOp) -> str:
        """Generate C code for a binary operation."""
        left = self.generate(expr.left)
        right = self.generate(expr.right)
        op = self._get_binop_str(expr.op)
        return f"({left} {op} {right})"

    def _get_binop_str(self, op: ast.operator) -> str:
        """Get C operator string for binary operation."""
        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
            ast.LShift: "<<",
            ast.RShift: ">>",
            ast.BitOr: "|",
            ast.BitXor: "^",
            ast.BitAnd: "&",
        }
        return op_map.get(type(op), "?")

    def _gen_compare(self, expr: ast.Compare) -> str:
        """Generate C code for a comparison."""
        left = self.generate(expr.left)
        # Handle chained comparisons
        parts = [left]
        for op, comparator in zip(expr.ops, expr.comparators):
            op_str = self._get_cmpop_str(op)
            right = self.generate(comparator)
            parts.append(f"{op_str} {right}")
        return "(" + " ".join(parts) + ")"

    def _get_cmpop_str(self, op: ast.cmpop) -> str:
        """Get C operator string for comparison."""
        op_map = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }
        return op_map.get(type(op), "?")

    def _gen_attribute(self, expr: ast.Attribute) -> str:
        """Generate C code for attribute access."""
        value = self.generate(expr.value)
        if value == "self":
            return f"self->{expr.attr}"
        return f"{value}->{expr.attr}"

    def _gen_unaryop(self, expr: ast.UnaryOp) -> str:
        """Generate C code for a unary operation."""
        operand = self.generate(expr.operand)
        op_map = {
            ast.UAdd: "+",
            ast.USub: "-",
            ast.Not: "!",
            ast.Invert: "~",
        }
        op_str = op_map.get(type(expr.op), "?")
        return f"({op_str}{operand})"

    def _gen_subscript(self, expr: ast.Subscript) -> str:
        """Generate C code for subscript access."""
        value = self.generate(expr.value)
        index = self.generate(expr.slice)
        return f"{value}[{index}]"

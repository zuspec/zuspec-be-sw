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
        elif isinstance(expr, ast.Await):
            return self._gen_await(expr)
        else:
            return f"/* unsupported expr: {type(expr).__name__} */"

    def _gen_await(self, expr: ast.Await) -> str:
        """Generate C code for an await expression.
        
        Note: This generates a placeholder comment. Actual await handling
        requires coroutine transformation done by AsyncMethodGenerator.
        """
        awaited = self.generate(expr.value)
        return f"/* await {awaited} */"

    def _gen_call(self, expr: ast.Call) -> str:
        """Generate C code for a function call."""
        func_name = self._get_func_name(expr.func)

        # Handle special builtins
        if func_name == "print":
            return self._gen_print_call(expr.args)
        elif func_name == "range":
            # Range is handled specially in for loops
            args = [self.generate(arg) for arg in expr.args]
            return f"range({', '.join(args)})"
        else:
            args = [self.generate(arg) for arg in expr.args]
            return f"{func_name}({', '.join(args)})"

    def _get_func_name(self, func: ast.expr) -> str:
        """Extract function name from call expression."""
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            value = self.generate(func.value)
            return f"{value}->{func.attr}"
        return "unknown_func"

    def _gen_print_call(self, args: List[ast.expr]) -> str:
        """Generate C fprintf call from print arguments."""
        if not args:
            return 'fprintf(stdout, "\\n")'
        
        arg = args[0]
        
        # Check for format string: print("format %s" % value)
        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
            # This is a % format expression
            return self._gen_print_format(arg)
        
        # Simple argument
        arg_code = self.generate(arg)
        if arg_code.startswith('"') and arg_code.endswith('"'):
            # String literal - add newline
            format_str = arg_code[:-1] + '\\n"'
            return f"fprintf(stdout, {format_str})"
        else:
            # Variable - use %s format
            return f'fprintf(stdout, "%s\\n", {arg_code})'

    def _gen_print_format(self, binop: ast.BinOp) -> str:
        """Generate fprintf for print("format %s" % value) pattern."""
        format_expr = binop.left
        value_expr = binop.right
        
        # Get format string
        if isinstance(format_expr, ast.Constant) and isinstance(format_expr.value, str):
            format_str = format_expr.value
        else:
            # Not a constant format string - fall back to runtime
            format_code = self.generate(format_expr)
            value_code = self.generate(value_expr)
            return f'fprintf(stdout, "%s\\n", /* format */ {format_code}, {value_code})'
        
        # Parse format string and map Python format specifiers to C
        c_format = self._convert_format_string(format_str)
        
        # Get the value(s) - could be tuple or single value
        if isinstance(value_expr, ast.Tuple):
            values = [self.generate(e) for e in value_expr.elts]
        else:
            values = [self.generate(value_expr)]
        
        # Add newline to format
        c_format_str = f'"{c_format}\\n"'
        
        if values:
            return f'fprintf(stdout, {c_format_str}, {", ".join(values)})'
        else:
            return f'fprintf(stdout, {c_format_str})'

    def _convert_format_string(self, py_format: str) -> str:
        """Convert Python format string to C printf format."""
        # Escape for C string and handle format specifiers
        result = py_format.replace('\\', '\\\\').replace('"', '\\"')
        
        # Python %s -> C %s (works the same for most cases)
        # Python %d -> C %d (same)
        # Python %f -> C %f (same)
        # For now, just return as-is since basic specifiers match
        return result

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

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
Statement code generation for converting Python AST statements to C code.
"""
import ast
from typing import List

from .expr_generator import ExprGenerator


class StmtGenerator:
    """Generates C code from Python AST statements."""

    def __init__(self):
        self.expr_gen = ExprGenerator()
        self.indent_level = 0
        self.indent_str = "    "

    def generate(self, stmts: List[ast.stmt]) -> str:
        """Generate C code for a list of statements."""
        lines = []
        for stmt in stmts:
            lines.append(self._gen_stmt(stmt))
        return "\n".join(lines)

    def _indent(self) -> str:
        """Get current indentation string."""
        return self.indent_str * self.indent_level

    def _gen_stmt(self, stmt: ast.stmt) -> str:
        """Generate C code for a single statement."""
        if isinstance(stmt, ast.Expr):
            return self._gen_expr_stmt(stmt)
        elif isinstance(stmt, ast.Assign):
            return self._gen_assign(stmt)
        elif isinstance(stmt, ast.AugAssign):
            return self._gen_aug_assign(stmt)
        elif isinstance(stmt, ast.If):
            return self._gen_if(stmt)
        elif isinstance(stmt, ast.For):
            return self._gen_for(stmt)
        elif isinstance(stmt, ast.While):
            return self._gen_while(stmt)
        elif isinstance(stmt, ast.Return):
            return self._gen_return(stmt)
        elif isinstance(stmt, ast.Pass):
            return f"{self._indent()}/* pass */"
        elif isinstance(stmt, ast.Break):
            return f"{self._indent()}break;"
        elif isinstance(stmt, ast.Continue):
            return f"{self._indent()}continue;"
        else:
            return f"{self._indent()}/* unsupported stmt: {type(stmt).__name__} */"

    def _gen_expr_stmt(self, stmt: ast.Expr) -> str:
        """Generate C code for an expression statement."""
        expr_code = self.expr_gen.generate(stmt.value)
        return f"{self._indent()}{expr_code};"

    def _gen_assign(self, stmt: ast.Assign) -> str:
        """Generate C code for an assignment."""
        value = self.expr_gen.generate(stmt.value)
        targets = [self.expr_gen.generate(t) for t in stmt.targets]
        # For simplicity, handle single target
        target = targets[0]
        return f"{self._indent()}{target} = {value};"

    def _gen_aug_assign(self, stmt: ast.AugAssign) -> str:
        """Generate C code for an augmented assignment (+=, etc)."""
        target = self.expr_gen.generate(stmt.target)
        value = self.expr_gen.generate(stmt.value)
        op = self._get_aug_op(stmt.op)
        return f"{self._indent()}{target} {op}= {value};"

    def _get_aug_op(self, op: ast.operator) -> str:
        """Get C operator string for augmented assignment."""
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

    def _gen_if(self, stmt: ast.If) -> str:
        """Generate C code for an if statement."""
        lines = []
        test = self.expr_gen.generate(stmt.test)
        lines.append(f"{self._indent()}if ({test}) {{")
        
        self.indent_level += 1
        for s in stmt.body:
            lines.append(self._gen_stmt(s))
        self.indent_level -= 1
        
        if stmt.orelse:
            if len(stmt.orelse) == 1 and isinstance(stmt.orelse[0], ast.If):
                # else if
                lines.append(f"{self._indent()}}} else {self._gen_if(stmt.orelse[0]).lstrip()}")
                return "\n".join(lines)
            else:
                lines.append(f"{self._indent()}}} else {{")
                self.indent_level += 1
                for s in stmt.orelse:
                    lines.append(self._gen_stmt(s))
                self.indent_level -= 1
        
        lines.append(f"{self._indent()}}}")
        return "\n".join(lines)

    def _gen_for(self, stmt: ast.For) -> str:
        """Generate C code for a for loop."""
        lines = []
        target = self.expr_gen.generate(stmt.target)
        
        # Check if this is a range() loop
        if isinstance(stmt.iter, ast.Call):
            func = stmt.iter.func
            if isinstance(func, ast.Name) and func.id == "range":
                return self._gen_range_for(stmt, target)
        
        # Generic iteration - not fully supported
        lines.append(f"{self._indent()}/* for loop over iterable - not fully supported */")
        return "\n".join(lines)

    def _gen_range_for(self, stmt: ast.For, target: str) -> str:
        """Generate C for loop from range()."""
        lines = []
        args = stmt.iter.args
        
        if len(args) == 1:
            start = "0"
            end = self.expr_gen.generate(args[0])
            step = "1"
        elif len(args) == 2:
            start = self.expr_gen.generate(args[0])
            end = self.expr_gen.generate(args[1])
            step = "1"
        else:
            start = self.expr_gen.generate(args[0])
            end = self.expr_gen.generate(args[1])
            step = self.expr_gen.generate(args[2])

        lines.append(f"{self._indent()}for (int {target} = {start}; {target} < {end}; {target} += {step}) {{")
        
        self.indent_level += 1
        for s in stmt.body:
            lines.append(self._gen_stmt(s))
        self.indent_level -= 1
        
        lines.append(f"{self._indent()}}}")
        return "\n".join(lines)

    def _gen_while(self, stmt: ast.While) -> str:
        """Generate C code for a while loop."""
        lines = []
        test = self.expr_gen.generate(stmt.test)
        lines.append(f"{self._indent()}while ({test}) {{")
        
        self.indent_level += 1
        for s in stmt.body:
            lines.append(self._gen_stmt(s))
        self.indent_level -= 1
        
        lines.append(f"{self._indent()}}}")
        return "\n".join(lines)

    def _gen_return(self, stmt: ast.Return) -> str:
        """Generate C code for a return statement."""
        if stmt.value:
            value = self.expr_gen.generate(stmt.value)
            return f"{self._indent()}return {value};"
        return f"{self._indent()}return;"

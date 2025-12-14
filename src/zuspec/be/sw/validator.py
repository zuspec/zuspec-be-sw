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
Validator for checking that datamodel representation can be mapped to C.
"""
import ast
from typing import List, Optional
from zuspec.dataclasses import dm


class ValidationError:
    """Represents a validation error."""
    def __init__(self, message: str, location: Optional[str] = None):
        self.message = message
        self.location = location

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.message}"
        return self.message


class CValidator:
    """Validates that a datamodel can be mapped to C."""

    # Supported AST node types for expressions
    SUPPORTED_EXPR_TYPES = {
        ast.Call,
        ast.Constant,
        ast.Name,
        ast.BinOp,
        ast.Compare,
        ast.Attribute,
        ast.UnaryOp,
        ast.Subscript,
    }

    # Supported AST node types for statements
    SUPPORTED_STMT_TYPES = {
        ast.Expr,
        ast.Assign,
        ast.AugAssign,
        ast.If,
        ast.For,
        ast.While,
        ast.Return,
        ast.Pass,
        ast.Break,
        ast.Continue,
    }

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []

    def validate(self, ctxt: dm.Context) -> bool:
        """Validate all types in the context."""
        for name, dtype in ctxt.type_m.items():
            self._validate_type(dtype)
        return self.is_valid()

    def validate_component(self, comp: dm.DataTypeComponent) -> bool:
        """Validate a single component."""
        self._validate_type(comp)
        return self.is_valid()

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0

    def _validate_type(self, dtype: dm.DataType):
        """Validate a datamodel type."""
        if isinstance(dtype, dm.DataTypeComponent):
            self._validate_component(dtype)
        elif isinstance(dtype, dm.DataTypeStruct):
            self._validate_struct(dtype)
        elif isinstance(dtype, dm.DataTypeProtocol):
            self._validate_protocol(dtype)

    def _validate_component(self, comp: dm.DataTypeComponent):
        """Validate a component type."""
        for field in comp.fields:
            self._validate_field(field)
        
        for func in comp.functions:
            self._validate_function(func, comp.name)

    def _validate_struct(self, struct: dm.DataTypeStruct):
        """Validate a struct type."""
        for field in struct.fields:
            self._validate_field(field)

    def _validate_protocol(self, proto: dm.DataTypeProtocol):
        """Validate a protocol type."""
        # Protocols map to vtables in C
        pass

    def _validate_field(self, field: dm.Field):
        """Validate a field."""
        # Fields need type annotations for C
        if field.dtype is None:
            self.errors.append(ValidationError(
                f"Field '{field.name}' missing type annotation"
            ))

    def _validate_function(self, func: dm.Function, type_name: str):
        """Validate a function."""
        location = f"{type_name}.{func.name}"
        
        # Skip internal/inherited methods
        if func.name.startswith("__") and func.name != "__init__":
            return
        if func.name in ("shutdown", "time", "wait", "__bind__"):
            return

        # Check argument annotations
        if func.args:
            for arg in func.args.args:
                if arg.annotation is None:
                    self.warnings.append(
                        f"{location}: Argument '{arg.arg}' missing type annotation"
                    )

    def validate_ast(self, tree: ast.AST, location: str = "") -> bool:
        """Validate that a Python AST can be mapped to C."""
        if isinstance(tree, ast.Module):
            for stmt in tree.body:
                self._validate_ast_stmt(stmt, location)
        elif isinstance(tree, ast.FunctionDef):
            for stmt in tree.body:
                self._validate_ast_stmt(stmt, f"{location}.{tree.name}")
        return self.is_valid()

    def _validate_ast_stmt(self, stmt: ast.stmt, location: str):
        """Validate a statement AST node."""
        if type(stmt) not in self.SUPPORTED_STMT_TYPES:
            self.errors.append(ValidationError(
                f"Unsupported statement type: {type(stmt).__name__}",
                location
            ))
            return

        # Validate contained expressions
        if isinstance(stmt, ast.Expr):
            self._validate_ast_expr(stmt.value, location)
        elif isinstance(stmt, ast.Assign):
            self._validate_ast_expr(stmt.value, location)
            for target in stmt.targets:
                self._validate_ast_expr(target, location)
        elif isinstance(stmt, ast.If):
            self._validate_ast_expr(stmt.test, location)
            for s in stmt.body:
                self._validate_ast_stmt(s, location)
            for s in stmt.orelse:
                self._validate_ast_stmt(s, location)
        elif isinstance(stmt, ast.For):
            self._validate_ast_expr(stmt.target, location)
            self._validate_ast_expr(stmt.iter, location)
            for s in stmt.body:
                self._validate_ast_stmt(s, location)
        elif isinstance(stmt, ast.While):
            self._validate_ast_expr(stmt.test, location)
            for s in stmt.body:
                self._validate_ast_stmt(s, location)
        elif isinstance(stmt, ast.Return):
            if stmt.value:
                self._validate_ast_expr(stmt.value, location)

    def _validate_ast_expr(self, expr: ast.expr, location: str):
        """Validate an expression AST node."""
        if type(expr) not in self.SUPPORTED_EXPR_TYPES:
            self.errors.append(ValidationError(
                f"Unsupported expression type: {type(expr).__name__}",
                location
            ))
            return

        # Recursively validate sub-expressions
        if isinstance(expr, ast.Call):
            self._validate_ast_expr(expr.func, location)
            for arg in expr.args:
                self._validate_ast_expr(arg, location)
        elif isinstance(expr, ast.BinOp):
            self._validate_ast_expr(expr.left, location)
            self._validate_ast_expr(expr.right, location)
        elif isinstance(expr, ast.Compare):
            self._validate_ast_expr(expr.left, location)
            for comp in expr.comparators:
                self._validate_ast_expr(comp, location)
        elif isinstance(expr, ast.Attribute):
            self._validate_ast_expr(expr.value, location)
        elif isinstance(expr, ast.UnaryOp):
            self._validate_ast_expr(expr.operand, location)
        elif isinstance(expr, ast.Subscript):
            self._validate_ast_expr(expr.value, location)
            self._validate_ast_expr(expr.slice, location)

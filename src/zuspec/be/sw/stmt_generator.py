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
Statement code generation for converting datamodel statements to C code.
"""
from typing import List


class StmtGenerator:
    """Generates C code from datamodel statements."""

    def __init__(self, component=None, ctxt=None):
        """Initialize statement generator.
        
        Args:
            component: The dm.DataTypeComponent being generated (for field name lookup)
            ctxt: The dm.Context for type resolution
        """
        self.indent_level = 0
        self.indent_str = "    "
        self.component = component
        self.ctxt = ctxt

    def _indent(self) -> str:
        """Get current indentation string."""
        return self.indent_str * self.indent_level

    # Methods for generating from datamodel statements
    def _gen_dm_stmt(self, stmt) -> str:
        """Generate C code from a datamodel statement."""
        from zuspec.dataclasses import dm
        
        if isinstance(stmt, dm.StmtExpr):
            # Skip docstring literals (standalone string expressions)
            if isinstance(stmt.expr, dm.ExprConstant) and isinstance(stmt.expr.value, str):
                return ""
            expr_code = self._gen_dm_expr(stmt.expr)
            return f"{self._indent()}{expr_code};"
        elif isinstance(stmt, dm.StmtAssign):
            targets = [self._gen_dm_expr(t) for t in stmt.targets]
            value = self._gen_dm_expr(stmt.value)
            return f"{self._indent()}{targets[0]} = {value};"
        elif isinstance(stmt, dm.StmtReturn):
            if stmt.value:
                value = self._gen_dm_expr(stmt.value)
                return f"{self._indent()}return {value};"
            return f"{self._indent()}return;"
        elif isinstance(stmt, dm.StmtPass):
            return f"{self._indent()}/* pass */"
        elif isinstance(stmt, dm.StmtFor):
            return self._gen_dm_for(stmt)
        elif isinstance(stmt, dm.StmtIf):
            return self._gen_dm_if(stmt)
        elif isinstance(stmt, dm.StmtWhile):
            return self._gen_dm_while(stmt)
        elif isinstance(stmt, dm.StmtBreak):
            return f"{self._indent()}break;"
        elif isinstance(stmt, dm.StmtContinue):
            return f"{self._indent()}continue;"
        else:
            return f"{self._indent()}/* unsupported dm stmt: {type(stmt).__name__} */"

    def _gen_dm_expr(self, expr) -> str:
        """Generate C code from a datamodel expression."""
        from zuspec.dataclasses import dm
        
        if isinstance(expr, dm.ExprConstant):
            return self._gen_dm_constant(expr)
        elif isinstance(expr, dm.ExprCall):
            return self._gen_dm_call(expr)
        elif isinstance(expr, dm.TypeExprRefSelf):
            return "self"
        elif isinstance(expr, dm.ExprRefField):
            return self._gen_dm_field_ref(expr)
        elif isinstance(expr, dm.ExprRefParam):
            return expr.name
        elif isinstance(expr, dm.ExprRefLocal):
            return expr.name
        elif isinstance(expr, dm.ExprRefUnresolved):
            # Unresolved names are likely builtins or external references
            return expr.name
        elif isinstance(expr, dm.ExprAttribute):
            value = self._gen_dm_expr(expr.value)
            # Use -> for pointer access from self, . for struct member access
            if isinstance(expr.value, dm.TypeExprRefSelf):
                return f"{value}->{expr.attr}"
            elif isinstance(expr.value, dm.ExprRefField):
                # Field access - determine if pointer or embedded based on field type
                return f"{value}.{expr.attr}"
            return f"{value}->{expr.attr}"
        elif isinstance(expr, dm.ExprBin):
            left = self._gen_dm_expr(expr.lhs)
            right = self._gen_dm_expr(expr.rhs)
            op = self._get_dm_binop(expr.op)
            return f"({left} {op} {right})"
        elif isinstance(expr, dm.ExprAwait):
            # Await in non-async context - just generate the awaited expression
            return self._gen_dm_expr(expr.value)
        else:
            return f"/* unsupported dm expr: {type(expr).__name__} */"

    def _gen_dm_field_ref(self, expr) -> str:
        """Generate C code for a field reference (ExprRefField)."""
        from zuspec.dataclasses import dm
        
        base = self._gen_dm_expr(expr.base)
        index = expr.index
        
        # Get field name from component's field list
        field_name = self._get_field_name_by_index(expr.base, index)
        
        # Determine accessor based on base type
        if isinstance(expr.base, dm.TypeExprRefSelf):
            return f"{base}->{field_name}"
        else:
            # Nested field access - need to determine type of base
            return f"{base}.{field_name}"

    def _get_field_name_by_index(self, base_expr, index: int) -> str:
        """Get field name from index, resolving through the type chain."""
        from zuspec.dataclasses import dm
        
        if isinstance(base_expr, dm.TypeExprRefSelf):
            # Direct field of current component
            if self.component and index < len(self.component.fields):
                return self.component.fields[index].name
        elif isinstance(base_expr, dm.ExprRefField):
            # Nested field - need to resolve the type of the base field
            base_type = self._get_field_type(base_expr)
            if base_type and isinstance(base_type, dm.DataTypeComponent):
                if index < len(base_type.fields):
                    return base_type.fields[index].name
            elif base_type and isinstance(base_type, dm.DataTypeRef) and self.ctxt:
                resolved = self.ctxt.type_m.get(base_type.ref_name)
                if resolved and isinstance(resolved, dm.DataTypeComponent):
                    if index < len(resolved.fields):
                        return resolved.fields[index].name
        
        # Fallback to index-based name
        return f"field_{index}"

    def _get_field_type(self, expr):
        """Get the datatype of a field expression."""
        from zuspec.dataclasses import dm
        
        if isinstance(expr, dm.ExprRefField):
            base_type = self._get_field_type(expr.base) if not isinstance(expr.base, dm.TypeExprRefSelf) else None
            
            if isinstance(expr.base, dm.TypeExprRefSelf):
                # Direct field of component
                if self.component and expr.index < len(self.component.fields):
                    dtype = self.component.fields[expr.index].datatype
                    # Resolve references
                    if isinstance(dtype, dm.DataTypeRef) and self.ctxt:
                        return self.ctxt.type_m.get(dtype.ref_name)
                    return dtype
            elif base_type:
                # Nested field
                if isinstance(base_type, dm.DataTypeComponent):
                    if expr.index < len(base_type.fields):
                        dtype = base_type.fields[expr.index].datatype
                        if isinstance(dtype, dm.DataTypeRef) and self.ctxt:
                            return self.ctxt.type_m.get(dtype.ref_name)
                        return dtype
        
        return None

    def _gen_dm_constant(self, expr) -> str:
        """Generate C code for a datamodel constant."""
        if isinstance(expr.value, str):
            escaped = expr.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'"{escaped}"'
        elif isinstance(expr.value, bool):
            return "1" if expr.value else "0"
        elif isinstance(expr.value, (int, float)):
            return str(expr.value)
        elif expr.value is None:
            return "NULL"
        return str(expr.value)

    def _gen_dm_call(self, expr) -> str:
        """Generate C code for a datamodel function call."""
        from zuspec.dataclasses import dm
        
        func = expr.func
        args = [self._gen_dm_expr(arg) for arg in expr.args]
        
        # Handle print() builtin - can be ExprConstant or ExprRefUnresolved
        if isinstance(func, dm.ExprConstant) and func.value == "print":
            return self._gen_dm_print(expr.args)
        if isinstance(func, dm.ExprRefUnresolved) and func.name == "print":
            return self._gen_dm_print(expr.args)
        
        # Handle range() builtin
        if isinstance(func, dm.ExprRefUnresolved) and func.name == "range":
            # range() is handled at statement level for for-loops
            args_str = ', '.join(args)
            return f"range({args_str})"
        
        # Handle method calls
        if isinstance(func, dm.ExprAttribute):
            # Check for self.method() - direct method call on component
            if isinstance(func.value, dm.TypeExprRefSelf):
                # self.method() -> method call (handled by vtable or direct)
                return f"/* self.{func.attr}({', '.join(args)}) - direct method call */"
            
            # Check for self.field.method() - could be port call or memory access
            if isinstance(func.value, dm.ExprRefField):
                # This is a call through a field - check if it's a port or memory
                field_type = self._get_field_type(func.value)
                base_code = self._gen_dm_expr(func.value)
                
                if self._is_port_type(func.value):
                    # Port call: self->port->method(self->port->self, args)
                    return f"{base_code}->{func.attr}({base_code}->self, {', '.join(args)})"
                elif self._is_memory_type(func.value):
                    # Memory read/write: zsp_memory_read(&self->mem, addr) or zsp_memory_write(&self->mem, addr, data)
                    if func.attr == "read":
                        return f"zsp_memory_read(&{base_code}, {', '.join(args)})"
                    elif func.attr == "write":
                        return f"zsp_memory_write(&{base_code}, {', '.join(args)})"
                    else:
                        # Unknown memory method
                        return f"{base_code}.{func.attr}({', '.join(args)})"
                else:
                    # Regular field method call
                    return f"{base_code}.{func.attr}({', '.join(args)})"
            
            # Generic attribute call
            value = self._gen_dm_expr(func.value)
            return f"{value}->{func.attr}({', '.join(args)})"
        
        func_name = self._gen_dm_expr(func)
        return f"{func_name}({', '.join(args)})"

    def _is_port_type(self, expr) -> bool:
        """Check if an expression refers to a port field."""
        from zuspec.dataclasses import dm
        
        if isinstance(expr, dm.ExprRefField):
            if isinstance(expr.base, dm.TypeExprRefSelf):
                # Direct field of component
                if self.component and expr.index < len(self.component.fields):
                    return self.component.fields[expr.index].kind == dm.FieldKind.Port
        return False

    def _is_memory_type(self, expr) -> bool:
        """Check if an expression refers to a memory field."""
        from zuspec.dataclasses import dm
        
        if isinstance(expr, dm.ExprRefField):
            field_type = self._get_field_type(expr)
            return isinstance(field_type, dm.DataTypeMemory)
        return False

    def _gen_dm_print(self, args) -> str:
        """Generate fprintf for print()."""
        from zuspec.dataclasses import dm
        
        if not args:
            return 'fprintf(stdout, "\\n")'
        
        arg = args[0]
        
        # Check for format string
        if isinstance(arg, dm.ExprBin) and arg.op == dm.BinOp.Mod:
            format_expr = arg.lhs
            value_expr = arg.rhs
            if isinstance(format_expr, dm.ExprConstant) and isinstance(format_expr.value, str):
                format_str = format_expr.value.replace('\\', '\\\\').replace('"', '\\"')
                value_code = self._gen_dm_expr(value_expr)
                return f'fprintf(stdout, "{format_str}\\n", {value_code})'
        
        # Simple argument
        if isinstance(arg, dm.ExprConstant) and isinstance(arg.value, str):
            escaped = arg.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'fprintf(stdout, "{escaped}\\n")'
        
        arg_code = self._gen_dm_expr(arg)
        return f'fprintf(stdout, "%s\\n", {arg_code})'

    def _get_dm_binop(self, op) -> str:
        """Get C operator string for datamodel binary operation."""
        from zuspec.dataclasses import dm
        op_map = {
            dm.BinOp.Add: "+",
            dm.BinOp.Sub: "-",
            dm.BinOp.Mult: "*",
            dm.BinOp.Div: "/",
            dm.BinOp.Mod: "%",
            dm.BinOp.LShift: "<<",
            dm.BinOp.RShift: ">>",
            dm.BinOp.BitOr: "|",
            dm.BinOp.BitXor: "^",
            dm.BinOp.BitAnd: "&",
        }
        return op_map.get(op, "?")

    def _gen_dm_for(self, stmt) -> str:
        """Generate C for loop from datamodel."""
        lines = []
        target = self._gen_dm_expr(stmt.target)
        
        # Check for range iteration
        iter_expr = stmt.iter
        from zuspec.dataclasses import dm
        if isinstance(iter_expr, dm.ExprCall):
            func_name = None
            if isinstance(iter_expr.func, dm.ExprConstant) and iter_expr.func.value == "range":
                func_name = "range"
            elif isinstance(iter_expr.func, dm.ExprRefUnresolved) and iter_expr.func.name == "range":
                func_name = "range"
            
            if func_name == "range":
                return self._gen_dm_range_for(stmt, target, iter_expr.args)
        
        lines.append(f"{self._indent()}/* for loop - not fully supported */")
        return "\n".join(lines)

    def _gen_dm_range_for(self, stmt, target: str, args: list) -> str:
        """Generate C for loop from range()."""
        lines = []
        
        if len(args) == 1:
            start = "0"
            end = self._gen_dm_expr(args[0])
            step = "1"
        elif len(args) == 2:
            start = self._gen_dm_expr(args[0])
            end = self._gen_dm_expr(args[1])
            step = "1"
        else:
            start = self._gen_dm_expr(args[0])
            end = self._gen_dm_expr(args[1])
            step = self._gen_dm_expr(args[2])

        lines.append(f"{self._indent()}for (int {target} = {start}; {target} < {end}; {target} += {step}) {{")
        
        self.indent_level += 1
        for s in stmt.body:
            lines.append(self._gen_dm_stmt(s))
        self.indent_level -= 1
        
        lines.append(f"{self._indent()}}}")
        return "\n".join(lines)

    def _gen_dm_if(self, stmt) -> str:
        """Generate C if statement from datamodel."""
        lines = []
        test = self._gen_dm_expr(stmt.test)
        lines.append(f"{self._indent()}if ({test}) {{")
        
        self.indent_level += 1
        for s in stmt.body:
            lines.append(self._gen_dm_stmt(s))
        self.indent_level -= 1
        
        if stmt.orelse:
            lines.append(f"{self._indent()}}} else {{")
            self.indent_level += 1
            for s in stmt.orelse:
                lines.append(self._gen_dm_stmt(s))
            self.indent_level -= 1
        
        lines.append(f"{self._indent()}}}")
        return "\n".join(lines)

    def _gen_dm_while(self, stmt) -> str:
        """Generate C while loop from datamodel."""
        lines = []
        test = self._gen_dm_expr(stmt.test)
        lines.append(f"{self._indent()}while ({test}) {{")
        
        self.indent_level += 1
        for s in stmt.body:
            lines.append(self._gen_dm_stmt(s))
        self.indent_level -= 1
        
        lines.append(f"{self._indent()}}}")
        return "\n".join(lines)

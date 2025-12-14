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
Async method code generation from datamodel - transforms datamodel async methods to C coroutines.

This module converts async method bodies represented in the datamodel into C coroutine
functions using the switch/case pattern used by the zsp_timebase runtime.
"""
from typing import List, Tuple, Optional
from zuspec.dataclasses import dm


class DmAsyncMethodGenerator:
    """
    Generates C coroutine code from datamodel async method definitions.
    
    Transforms async methods into switch/case based coroutines that work
    with the zsp_timebase scheduling system.
    """

    def __init__(self, component_name: str, method_name: str, component: dm.DataTypeComponent = None, ctxt: dm.Context = None):
        self.component_name = component_name
        self.method_name = method_name
        self.component = component
        self.ctxt = ctxt
        self.indent_str = "    "

    def generate(self, func: dm.Function) -> str:
        """Generate C coroutine function from datamodel Function."""
        # Analyze the method to find await points
        blocks = self._split_at_awaits(func.body)
        
        # Generate the coroutine function
        lines = []
        func_name = f"{self.component_name}_{self.method_name}"
        
        # Function signature (coroutine task function)
        lines.append(f"static zsp_frame_t *{func_name}_task(")
        lines.append(f"        zsp_thread_t *thread,")
        lines.append(f"        int idx,")
        lines.append(f"        va_list *args) {{")
        lines.append(f"    zsp_frame_t *ret = thread->leaf;")
        lines.append(f"    zsp_timebase_t *tb = zsp_thread_timebase(thread);")
        lines.append(f"    (void)tb;  /* May be unused */")
        lines.append(f"")
        
        # Generate locals struct
        lines.append(f"    typedef struct {{")
        lines.append(f"        {self.component_name} *self;")
        lines.append(f"    }} locals_t;")
        lines.append(f"")
        
        # Switch statement
        lines.append(f"    switch (idx) {{")
        
        # Generate each block as a case
        for i, block in enumerate(blocks):
            lines.append(f"        case {i}: {{")
            
            if i == 0:
                # First block - allocate frame and extract args
                lines.append(f"            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &{func_name}_task);")
                lines.append(f"            locals_t *locals = zsp_frame_locals(ret, locals_t);")
                lines.append(f"            if (args) {{")
                lines.append(f"                locals->self = ({self.component_name} *)va_arg(*args, void *);")
                lines.append(f"            }}")
            else:
                lines.append(f"            locals_t *locals = zsp_frame_locals(ret, locals_t);")
            
            # Generate statements in this block
            block_stmts, await_expr = block
            for stmt in block_stmts:
                stmt_code = self._gen_stmt(stmt)
                for line in stmt_code.split('\n'):
                    if line.strip():
                        lines.append(f"            {line}")
            
            # Handle the await or end of function
            if await_expr is not None:
                # Set next index and yield
                lines.append(f"            ret->idx = {i + 1};")
                await_code = self._gen_await_code(await_expr)
                lines.append(f"            {await_code}")
                lines.append(f"            break;")
            else:
                # End of function - return
                lines.append(f"            ret = zsp_timebase_return(thread, 0);")
                lines.append(f"            break;")
            
            lines.append(f"        }}")
        
        lines.append(f"    }}")
        lines.append(f"    return ret;")
        lines.append(f"}}")
        lines.append(f"")
        
        # Generate wrapper function that starts the coroutine
        lines.append(f"void {func_name}({self.component_name} *self, zsp_timebase_t *tb) {{")
        lines.append(f"    zsp_thread_t *thread = zsp_timebase_thread_create(")
        lines.append(f"        tb, &{func_name}_task, ZSP_THREAD_FLAGS_NONE, self);")
        lines.append(f"    (void)thread;  /* Thread is managed by timebase */")
        lines.append(f"}}")
        
        return "\n".join(lines)

    def _split_at_awaits(self, stmts: List[dm.Stmt]) -> List[Tuple[List[dm.Stmt], Optional[dm.ExprAwait]]]:
        """
        Split statement list into blocks separated by await points.
        
        Returns list of (statements, await_expr) tuples. The await_expr is None
        for the final block if there's no trailing await.
        """
        blocks = []
        current_block = []
        
        for stmt in stmts:
            # Check if this statement contains an await
            await_expr = self._find_await(stmt)
            
            if await_expr:
                # Add current block with this await
                blocks.append((current_block.copy(), await_expr))
                current_block = []
            else:
                current_block.append(stmt)
        
        # Add final block (no await)
        if current_block:
            blocks.append((current_block, None))
        elif not blocks:
            # Empty method
            blocks.append(([], None))
        elif blocks[-1][1] is not None:
            # Method ends with await, add empty final block
            blocks.append(([], None))
            
        return blocks

    def _find_await(self, stmt: dm.Stmt) -> Optional[dm.ExprAwait]:
        """Find await expression in a statement, if any."""
        if isinstance(stmt, dm.StmtExpr):
            if isinstance(stmt.expr, dm.ExprAwait):
                return stmt.expr
        return None

    def _gen_stmt(self, stmt: dm.Stmt) -> str:
        """Generate C code for a datamodel statement."""
        if isinstance(stmt, dm.StmtExpr):
            expr_code = self._gen_expr(stmt.expr)
            return f"{expr_code};"
        elif isinstance(stmt, dm.StmtAssign):
            targets = [self._gen_expr(t) for t in stmt.targets]
            value = self._gen_expr(stmt.value)
            return f"{targets[0]} = {value};"
        elif isinstance(stmt, dm.StmtReturn):
            if stmt.value:
                return f"return {self._gen_expr(stmt.value)};"
            return "return;"
        elif isinstance(stmt, dm.StmtPass):
            return "/* pass */"
        elif isinstance(stmt, dm.StmtFor):
            return self._gen_for_stmt(stmt)
        else:
            return f"/* unsupported stmt: {type(stmt).__name__} */"

    def _gen_for_stmt(self, stmt: dm.StmtFor) -> str:
        """Generate C code for a for loop."""
        # Get the loop variable name
        if isinstance(stmt.target, dm.ExprRefLocal):
            loop_var = stmt.target.name
        elif isinstance(stmt.target, dm.ExprConstant):
            loop_var = str(stmt.target.value)
        else:
            loop_var = "i"
        
        # Handle range() iteration
        iter_expr = stmt.iter
        if isinstance(iter_expr, dm.ExprCall):
            func = iter_expr.func
            if isinstance(func, dm.ExprRefUnresolved) and func.name == "range":
                return self._gen_range_for(loop_var, iter_expr.args, stmt.body)
        
        # Fallback - generate as comment
        return f"/* unsupported for loop over {type(iter_expr).__name__} */"

    def _gen_range_for(self, loop_var: str, args: list, body: list) -> str:
        """Generate C for loop from range() call."""
        # Determine start, end, step from range args
        if len(args) == 1:
            start = "0"
            end = self._gen_expr(args[0])
            step = "1"
        elif len(args) == 2:
            start = self._gen_expr(args[0])
            end = self._gen_expr(args[1])
            step = "1"
        elif len(args) >= 3:
            start = self._gen_expr(args[0])
            end = self._gen_expr(args[1])
            step = self._gen_expr(args[2])
        else:
            return "/* invalid range() call */"
        
        # Generate the for loop
        lines = [f"for (int {loop_var} = {start}; {loop_var} < {end}; {loop_var} += {step}) {{"]
        for stmt in body:
            stmt_code = self._gen_stmt(stmt)
            for line in stmt_code.split('\n'):
                lines.append(f"    {line}")
        lines.append("}")
        
        return '\n'.join(lines)

    def _gen_expr(self, expr: dm.Expr) -> str:
        """Generate C code for a datamodel expression."""
        if isinstance(expr, dm.ExprCall):
            return self._gen_call(expr)
        elif isinstance(expr, dm.ExprConstant):
            return self._gen_constant(expr)
        elif isinstance(expr, dm.TypeExprRefSelf):
            return "locals->self"
        elif isinstance(expr, dm.ExprRefParam):
            return expr.name
        elif isinstance(expr, dm.ExprRefLocal):
            return expr.name
        elif isinstance(expr, dm.ExprRefUnresolved):
            return expr.name
        elif isinstance(expr, dm.ExprRefField):
            return self._gen_field_ref(expr)
        elif isinstance(expr, dm.ExprAttribute):
            return self._gen_attribute(expr)
        elif isinstance(expr, dm.ExprBin):
            return self._gen_binop(expr)
        elif isinstance(expr, dm.ExprAwait):
            # Await should be handled at statement level, not here
            return f"/* await {self._gen_expr(expr.value)} */"
        else:
            return f"/* unsupported expr: {type(expr).__name__} */"

    def _gen_field_ref(self, expr: dm.ExprRefField) -> str:
        """Generate C code for a field reference."""
        base = self._gen_expr(expr.base)
        field_name = self._get_field_name(expr.base, expr.index)
        
        if isinstance(expr.base, dm.TypeExprRefSelf):
            return f"{base}->{field_name}"
        else:
            return f"{base}.{field_name}"

    def _get_field_name(self, base_expr, index: int) -> str:
        """Get field name from index using component context."""
        if isinstance(base_expr, dm.TypeExprRefSelf):
            if self.component and index < len(self.component.fields):
                return self.component.fields[index].name
        elif isinstance(base_expr, dm.ExprRefField):
            # Nested field - resolve type
            base_type = self._get_field_type(base_expr)
            if base_type and isinstance(base_type, dm.DataTypeComponent):
                if index < len(base_type.fields):
                    return base_type.fields[index].name
        return f"field_{index}"

    def _get_field_type(self, expr: dm.ExprRefField):
        """Get the data type of a field expression."""
        if isinstance(expr.base, dm.TypeExprRefSelf):
            if self.component and expr.index < len(self.component.fields):
                dtype = self.component.fields[expr.index].datatype
                if isinstance(dtype, dm.DataTypeRef) and self.ctxt:
                    return self.ctxt.type_m.get(dtype.ref_name)
                return dtype
        return None

    def _is_port_field(self, expr: dm.ExprRefField) -> bool:
        """Check if a field reference is a port."""
        if isinstance(expr.base, dm.TypeExprRefSelf):
            if self.component and expr.index < len(self.component.fields):
                return self.component.fields[expr.index].kind == dm.FieldKind.Port
        return False

    def _gen_call(self, expr: dm.ExprCall) -> str:
        """Generate C code for a function call."""
        func = expr.func
        args = [self._gen_expr(arg) for arg in expr.args]

        # Handle special builtins
        func_name = self._get_func_name(func)
        if func_name == "print":
            return self._gen_print_call(expr.args)
        
        # Check for self.time() and self.wait() - Component built-in methods
        if isinstance(func, dm.ExprAttribute):
            is_self = (isinstance(func.value, dm.TypeExprRefSelf) or
                       (isinstance(func.value, dm.ExprConstant) and func.value.value == "self"))
            if is_self:
                if func.attr == "time":
                    # self.time() -> zsp_timebase_current_ticks(tb)
                    return "zsp_timebase_current_ticks(tb)"
                elif func.attr == "wait":
                    # self.wait() is handled at await level, but if called directly
                    # return a comment
                    return "/* self.wait() should be used with await */"
        
        return f"{func_name}({', '.join(args)})"

    def _get_func_name(self, func: dm.Expr) -> str:
        """Extract function name from call expression."""
        if isinstance(func, dm.ExprConstant):
            return str(func.value)
        elif isinstance(func, dm.ExprRefUnresolved):
            return func.name
        elif isinstance(func, dm.ExprAttribute):
            value = self._gen_expr(func.value)
            return f"{value}->{func.attr}"
        return "unknown_func"

    def _gen_print_call(self, args: List[dm.Expr]) -> str:
        """Generate C fprintf call from print arguments."""
        if not args:
            return 'fprintf(stdout, "\\n")'
        
        arg = args[0]
        
        # Check for format string: print("format %s" % value)
        if isinstance(arg, dm.ExprBin) and arg.op == dm.BinOp.Mod:
            return self._gen_print_format(arg)
        
        # Simple argument
        arg_code = self._gen_expr(arg)
        if isinstance(arg, dm.ExprConstant) and isinstance(arg.value, str):
            # String literal - escape and add newline
            escaped = arg.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'fprintf(stdout, "{escaped}\\n")'
        else:
            # Variable - use %s format
            return f'fprintf(stdout, "%s\\n", {arg_code})'

    def _gen_print_format(self, binop: dm.ExprBin) -> str:
        """Generate fprintf for print("format %s" % value) pattern."""
        format_expr = binop.lhs
        value_expr = binop.rhs
        
        # Get format string
        if isinstance(format_expr, dm.ExprConstant) and isinstance(format_expr.value, str):
            format_str = format_expr.value
            value_code = self._gen_expr(value_expr)
            
            # If value is self.time() (returns uint64_t), convert %s to %llu
            if self._is_time_call(value_expr):
                format_str = format_str.replace('%s', '%llu')
                value_code = f"(unsigned long long){value_code}"
            
            # Escape for C
            c_format = format_str.replace('\\', '\\\\').replace('"', '\\"')
            return f'fprintf(stdout, "{c_format}\\n", {value_code})'
        
        # Fallback
        format_code = self._gen_expr(format_expr)
        value_code = self._gen_expr(value_expr)
        return f'fprintf(stdout, "%s\\n", {format_code}, {value_code})'

    def _is_time_call(self, expr: dm.Expr) -> bool:
        """Check if expression is self.time() which returns uint64_t."""
        if isinstance(expr, dm.ExprCall):
            func = expr.func
            if isinstance(func, dm.ExprAttribute):
                is_self = (isinstance(func.value, dm.TypeExprRefSelf) or
                           (isinstance(func.value, dm.ExprConstant) and func.value.value == "self"))
                if is_self and func.attr == "time":
                    return True
        return False

    def _gen_constant(self, expr: dm.ExprConstant) -> str:
        """Generate C code for a constant value."""
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

    def _gen_attribute(self, expr: dm.ExprAttribute) -> str:
        """Generate C code for attribute access."""
        # Special case for TypeExprRefSelf -> access via locals->self
        if isinstance(expr.value, dm.TypeExprRefSelf):
            return f"locals->self->{expr.attr}"
        value = self._gen_expr(expr.value)
        if value == "self" or value == "locals->self":
            return f"locals->self->{expr.attr}"
        return f"{value}->{expr.attr}"

    def _gen_binop(self, expr: dm.ExprBin) -> str:
        """Generate C code for a binary operation."""
        left = self._gen_expr(expr.lhs)
        right = self._gen_expr(expr.rhs)
        op = self._get_binop_str(expr.op)
        return f"({left} {op} {right})"

    def _get_binop_str(self, op: dm.BinOp) -> str:
        """Get C operator string for binary operation."""
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

    def _gen_await_code(self, await_expr: dm.ExprAwait) -> str:
        """Generate C code for an await expression."""
        awaited = await_expr.value
        
        # Check what we're awaiting
        if isinstance(awaited, dm.ExprCall):
            func = awaited.func
            if isinstance(func, dm.ExprAttribute):
                # Check for self.wait()
                is_self = (isinstance(func.value, dm.TypeExprRefSelf) or
                           (isinstance(func.value, dm.ExprConstant) and func.value.value == "self"))
                if is_self:
                    if func.attr == "wait":
                        # await self.wait(time) -> zsp_timebase_wait(thread, time)
                        args = awaited.args
                        if args:
                            time_arg = self._gen_time_expr(args[0])
                            return f"zsp_timebase_wait(thread, {time_arg});"
        
        # Generic await - treat as yield
        return "zsp_timebase_yield(thread);"

    def _gen_time_expr(self, expr: dm.Expr) -> str:
        """Generate C code for a time expression (e.g., zdc.Time.ns(1))."""
        if isinstance(expr, dm.ExprCall):
            func = expr.func
            if isinstance(func, dm.ExprAttribute):
                # Look for Time.ns(), Time.us(), etc.
                if isinstance(func.value, dm.ExprAttribute):
                    # zdc.Time.ns(1)
                    time_class = func.value
                    if time_class.attr == "Time":
                        unit = func.attr  # ns, us, ms, etc.
                        if expr.args:
                            amount = self._gen_expr(expr.args[0])
                            return f"ZSP_TIME_{unit.upper()}({amount})"
                elif isinstance(func.value, dm.ExprConstant):
                    # Time.ns(1)
                    if func.value.value == "Time":
                        unit = func.attr
                        if expr.args:
                            amount = self._gen_expr(expr.args[0])
                            return f"ZSP_TIME_{unit.upper()}({amount})"
        
        # Fallback - use expression generator
        return self._gen_expr(expr)

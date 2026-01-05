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
from zuspec.dataclasses import ir


class DmAsyncMethodGenerator:
    """
    Generates C coroutine code from datamodel async method definitions.
    
    Transforms async methods into switch/case based coroutines that work
    with the zsp_timebase scheduling system.
    """

    def __init__(self, component_name: str, method_name: str, component: ir.DataTypeComponent = None, ctxt: ir.Context = None):
        self.component_name = component_name
        self.method_name = method_name
        self.component = component
        self.ctxt = ctxt
        self.indent_str = "    "

    def generate(self, func: ir.Function) -> str:
        """Generate C coroutine function from datamodel Function.
        
        Args:
            func: Function datamodel with populated body
            
        Raises:
            ValueError: If function body is empty or invalid
        """
        if not func.body:
            raise ValueError(
                f"Cannot generate async method '{self.method_name}': function body is empty. "
                f"Ensure the datamodel was built with proper source code available."
            )
        
        if self._is_trivial_wait_only(func):
            return self._generate_trivial_wait_only(func)

        # Analyze the method to find await points
        blocks = self._split_at_awaits(func.body)
        
        if not blocks:
            raise ValueError(
                f"Cannot generate async method '{self.method_name}': no executable blocks found. "
                f"Async methods must contain at least one statement."
            )
        
        # Get function parameters (excluding 'self')
        params = []
        if func.args and func.args.args:
            params = [arg for arg in func.args.args if arg.arg != 'self']
        
        # Generate the coroutine function
        lines = []
        func_name = f"{self.component_name}_{self.method_name}"
        
        # Function signature (coroutine task function)
        lines.append(f"static zsp_frame_t *{func_name}_task(")
        lines.append(f"        zsp_timebase_t *tb,")
        lines.append(f"        zsp_thread_t *thread,")
        lines.append(f"        int idx,")
        lines.append(f"        va_list *args) {{")
        lines.append(f"    zsp_frame_t *ret = thread->leaf;")
        lines.append(f"    (void)tb;  /* Timebase passed directly to avoid pointer chase */")
        lines.append(f"")
        
        # Generate locals struct
        local_vars = self._extract_local_vars(func.body, func.args)
        lines.append(f"    typedef struct {{")
        lines.append(f"        {self.component_name} *self;")
        for var_name, var_type in local_vars:
            lines.append(f"        {var_type} {var_name};")
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
                # Extract additional parameters
                for param in params:
                    c_type = self._get_param_c_type(param)
                    va_type = self._get_va_arg_type(c_type)
                    lines.append(f"                locals->{param.arg} = ({c_type})va_arg(*args, {va_type});")
                lines.append(f"            }}")
            else:
                lines.append(f"            locals_t *locals = zsp_frame_locals(ret, locals_t);")
                
                # If previous block had an await with a return value, handle it now
                if i > 0:
                    prev_block = blocks[i-1]
                    prev_await_stmt = prev_block[2]  # The statement containing the await
                    if prev_await_stmt and isinstance(prev_await_stmt, ir.StmtAssign):
                        # Previous await was an assignment, get the value from thread->rval
                        target = self._gen_expr(prev_await_stmt.targets[0])
                        lines.append(f"            {target} = (int)thread->rval;  /* Result from previous await */")
            
            # Generate statements in this block
            block_stmts, await_expr, await_stmt = block
            for stmt in block_stmts:
                stmt_code = self._gen_stmt(stmt)
                for line in stmt_code.split('\n'):
                    if line.strip():
                        lines.append(f"            {line}")
            
            # Handle the await or end of function
            if await_expr is not None:
                await_code = self._gen_await_code(await_expr, await_stmt)
                
                # Check if this is a wait() call that can be optimized
                if self._is_wait_call(await_expr):
                    lines.append(f"            if ({await_code}) {{")
                    lines.append(f"                ret->idx = {i + 1};")
                    lines.append(f"                break;  /* Suspended */")
                    lines.append(f"            }}")
                    lines.append(f"            /* Fall through - time advanced without suspension */")
                else:
                    # Other awaits (calls, channel ops) always suspend
                    lines.append(f"            ret->idx = {i + 1};")
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
        # Header uses: (self, params..., tb) so we must match
        wrapper_params = [f"{self.component_name} *self"]
        for param in params:
            c_type = self._get_param_c_type(param)
            wrapper_params.append(f"{c_type} {param.arg}")
        wrapper_params.append("zsp_timebase_t *tb")
        
        lines.append(f"void {func_name}({', '.join(wrapper_params)}) {{")
        
        # Build thread create call with all parameters
        create_args = ["self"]
        for param in params:
            create_args.append(param.arg)
        
        lines.append(f"    zsp_thread_t *thread = zsp_timebase_thread_create(")
        lines.append(f"        tb, &{func_name}_task, ZSP_THREAD_FLAGS_NONE, {', '.join(create_args)});")
        lines.append(f"    thread->exit_f = (zsp_thread_exit_f)&zsp_timebase_thread_free;")
        lines.append(f"}}")
        
        return "\n".join(lines)
    
    def _get_param_c_type(self, arg: ir.Arg) -> str:
        """Get C type for a function parameter from its annotation."""
        if arg.annotation:
            # Check for DataTypeInt or similar
            ann = arg.annotation
            if hasattr(ann, 'value'):
                val = ann.value
                if hasattr(val, '__name__'):
                    type_name = val.__name__
                    if type_name == 'int':
                        return 'int32_t'
                    elif type_name == 'float':
                        return 'float'
                    elif type_name == 'bool':
                        return 'int'
        return 'int32_t'  # Default
    
    def _get_va_arg_type(self, c_type: str) -> str:
        """Get the appropriate va_arg type for a C type."""
        if c_type in ('int8_t', 'int16_t', 'int32_t', 'int'):
            return 'int'
        elif c_type in ('uint8_t', 'uint16_t', 'uint32_t', 'unsigned'):
            return 'unsigned int'
        elif c_type == 'int64_t':
            return 'int64_t'
        elif c_type == 'uint64_t':
            return 'uint64_t'
        elif c_type == 'float':
            return 'double'
        elif c_type == 'double':
            return 'double'
        return 'int'

    def _extract_local_vars(self, stmts: List[ir.Stmt], args: ir.Arguments) -> List[Tuple[str, str]]:
        """
        Extract local variable declarations from function body.
        Returns list of (var_name, var_type) tuples.
        """
        local_vars = []
        seen_vars = set()
        
        # Add function parameters (if args exists)
        if args and args.args:
            for arg in args.args:
                if arg.arg != 'self' and arg.arg not in seen_vars:
                    # Determine type from annotation
                    var_type = self._get_param_c_type(arg)
                    local_vars.append((arg.arg, var_type))
                    seen_vars.add(arg.arg)
        
        # Walk statements to find assignments
        def extract_from_stmt(stmt):
            if isinstance(stmt, ir.StmtAssign):
                for target in stmt.targets:
                    if isinstance(target, ir.ExprRefLocal):
                        var_name = target.name
                        if var_name not in seen_vars:
                            # Determine type - for now assume int32_t
                            var_type = "int32_t"
                            local_vars.append((var_name, var_type))
                            seen_vars.add(var_name)
        
        for stmt in stmts:
            extract_from_stmt(stmt)
        
        return local_vars

    def _split_at_awaits(self, stmts: List[ir.Stmt]) -> List[Tuple[List[ir.Stmt], Optional[ir.ExprAwait], Optional[ir.Stmt]]]:
        """
        Split statement list into blocks separated by await points.
        
        Returns list of (statements, await_expr, await_stmt) tuples. 
        - statements: list of statements before the await
        - await_expr: the await expression (None for final block)
        - await_stmt: the full statement containing the await (for handling return values)
        """
        blocks = []
        current_block = []
        
        for stmt in stmts:
            # Check if this statement contains an await
            await_expr = self._find_await(stmt)
            
            if await_expr:
                # Add current block with this await (don't include the await statement in current_block)
                blocks.append((current_block.copy(), await_expr, stmt))
                current_block = []
            else:
                current_block.append(stmt)
        
        # Add final block (no await)
        if current_block:
            blocks.append((current_block, None, None))
        elif not blocks:
            # Empty method
            blocks.append(([], None, None))
        elif blocks[-1][1] is not None:
            # Method ends with await, add empty final block
            blocks.append(([], None, None))
            
        return blocks

    def _find_await(self, stmt: ir.Stmt) -> Optional[ir.ExprAwait]:
        """Find await expression in a statement, if any."""
        if isinstance(stmt, ir.StmtExpr):
            if isinstance(stmt.expr, ir.ExprAwait):
                return stmt.expr
        elif isinstance(stmt, ir.StmtAssign):
            # Check if the value being assigned contains an await
            if isinstance(stmt.value, ir.ExprAwait):
                return stmt.value
        elif isinstance(stmt, ir.StmtReturn):
            # Check if the return value contains an await
            if stmt.value and isinstance(stmt.value, ir.ExprAwait):
                return stmt.value
        return None

    def _gen_stmt(self, stmt: ir.Stmt) -> str:
        """Generate C code for a datamodel statement."""
        if isinstance(stmt, ir.StmtExpr):
            expr_code = self._gen_expr(stmt.expr)
            return f"{expr_code};"
        elif isinstance(stmt, ir.StmtAssign):
            targets = [self._gen_expr(t) for t in stmt.targets]
            value = self._gen_expr(stmt.value)
            return f"{targets[0]} = {value};"
        elif isinstance(stmt, ir.StmtReturn):
            if stmt.value:
                return f"return {self._gen_expr(stmt.value)};"
            return "return;"
        elif isinstance(stmt, ir.StmtPass):
            return "/* pass */"
        elif isinstance(stmt, ir.StmtFor):
            return self._gen_for_stmt(stmt)
        else:
            # Unsupported statement type - fail with clear error
            raise ValueError(
                f"Unsupported statement type in '{self.method_name}': {type(stmt).__name__}. "
                f"Supported statements: assignments, expressions, return, pass, for loops. "
                f"Add support for additional statement types if needed."
            )

    def _gen_for_stmt(self, stmt: ir.StmtFor) -> str:
        """Generate C code for a for loop."""
        # Get the loop variable name
        if isinstance(stmt.target, ir.ExprRefLocal):
            loop_var = stmt.target.name
        elif isinstance(stmt.target, ir.ExprConstant):
            loop_var = str(stmt.target.value)
        else:
            loop_var = "i"
        
        # Handle range() iteration
        iter_expr = stmt.iter
        if isinstance(iter_expr, ir.ExprCall):
            func = iter_expr.func
            if isinstance(func, ir.ExprRefUnresolved) and func.name == "range":
                return self._gen_range_for(loop_var, iter_expr.args, stmt.body)
        
        # Unsupported iteration type
        raise ValueError(
            f"Unsupported for loop in '{self.method_name}': iterating over {type(iter_expr).__name__}. "
            f"Currently only 'for x in range(...)' loops are supported. "
            f"Use range() for numeric iteration or implement support for other iterables."
        )

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

    def _gen_expr(self, expr: ir.Expr) -> str:
        """Generate C code for a datamodel expression."""
        if isinstance(expr, ir.ExprCall):
            return self._gen_call(expr)
        elif isinstance(expr, ir.ExprConstant):
            return self._gen_constant(expr)
        elif isinstance(expr, ir.TypeExprRefSelf):
            return "locals->self"
        elif isinstance(expr, ir.ExprRefParam):
            return f"locals->{expr.name}"
        elif isinstance(expr, ir.ExprRefLocal):
            return f"locals->{expr.name}"
        elif isinstance(expr, ir.ExprRefUnresolved):
            return expr.name
        elif isinstance(expr, ir.ExprRefField):
            return self._gen_field_ref(expr)
        elif isinstance(expr, ir.ExprAttribute):
            return self._gen_attribute(expr)
        elif isinstance(expr, ir.ExprBin):
            return self._gen_binop(expr)
        elif isinstance(expr, ir.ExprAwait):
            # Await should be handled at statement level, not here
            return f"/* await {self._gen_expr(expr.value)} */"
        else:
            return f"/* unsupported expr: {type(expr).__name__} */"

    def _gen_field_ref(self, expr: ir.ExprRefField) -> str:
        """Generate C code for a field reference."""
        base = self._gen_expr(expr.base)
        field_name = self._get_field_name(expr.base, expr.index)
        
        if isinstance(expr.base, ir.TypeExprRefSelf):
            return f"{base}->{field_name}"
        else:
            return f"{base}.{field_name}"

    def _get_field_name(self, base_expr, index: int) -> str:
        """Get field name from index using component context."""
        if isinstance(base_expr, ir.TypeExprRefSelf):
            if self.component and index < len(self.component.fields):
                return self.component.fields[index].name
        elif isinstance(base_expr, ir.ExprRefField):
            # Nested field - resolve type
            base_type = self._get_field_type(base_expr)
            if base_type and isinstance(base_type, ir.DataTypeComponent):
                if index < len(base_type.fields):
                    return base_type.fields[index].name
        return f"field_{index}"

    def _get_field_type(self, expr: ir.ExprRefField):
        """Get the data type of a field expression."""
        if isinstance(expr.base, ir.TypeExprRefSelf):
            if self.component and expr.index < len(self.component.fields):
                dtype = self.component.fields[expr.index].datatype
                if isinstance(dtype, ir.DataTypeRef) and self.ctxt:
                    return self.ctxt.type_m.get(dtype.ref_name)
                return dtype
        return None

    def _is_port_field(self, expr: ir.ExprRefField) -> bool:
        """Check if a field reference is a port."""
        if isinstance(expr.base, ir.TypeExprRefSelf):
            if self.component and expr.index < len(self.component.fields):
                return self.component.fields[expr.index].kind == ir.FieldKind.Port
        return False

    def _gen_call(self, expr: ir.ExprCall) -> str:
        """Generate C code for a function call."""
        func = expr.func
        args = [self._gen_expr(arg) for arg in expr.args]

        # Handle special builtins
        func_name = self._get_func_name(func)
        if func_name == "print":
            return self._gen_print_call(expr.args)
        
        # Check for self.time() and self.wait() - Component built-in methods
        if isinstance(func, ir.ExprAttribute):
            is_self = (isinstance(func.value, ir.TypeExprRefSelf) or
                       (isinstance(func.value, ir.ExprConstant) and func.value.value == "self"))
            if is_self:
                if func.attr == "time":
                    # self.time() -> zsp_timebase_current_ticks(tb)
                    return "zsp_timebase_current_ticks(tb)"
                elif func.attr == "wait":
                    # self.wait() is handled at await level, but if called directly
                    # return a comment
                    return "/* self.wait() should be used with await */"
        
        return f"{func_name}({', '.join(args)})"

    def _get_func_name(self, func: ir.Expr) -> str:
        """Extract function name from call expression."""
        if isinstance(func, ir.ExprConstant):
            return str(func.value)
        elif isinstance(func, ir.ExprRefUnresolved):
            return func.name
        elif isinstance(func, ir.ExprAttribute):
            value = self._gen_expr(func.value)
            return f"{value}->{func.attr}"
        return "unknown_func"

    def _gen_print_call(self, args: List[ir.Expr]) -> str:
        """Generate C fprintf call from print arguments."""
        if not args:
            return 'fprintf(stdout, "\\n")'
        
        arg = args[0]
        
        # Check for format string: print("format %s" % value)
        if isinstance(arg, ir.ExprBin) and arg.op == ir.BinOp.Mod:
            return self._gen_print_format(arg)
        
        # Simple argument
        arg_code = self._gen_expr(arg)
        if isinstance(arg, ir.ExprConstant) and isinstance(arg.value, str):
            # String literal - escape and add newline
            escaped = arg.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'fprintf(stdout, "{escaped}\\n")'
        else:
            # Variable - use %s format
            return f'fprintf(stdout, "%s\\n", {arg_code})'

    def _gen_print_format(self, binop: ir.ExprBin) -> str:
        """Generate fprintf for print("format %s" % value) pattern."""
        format_expr = binop.lhs
        value_expr = binop.rhs
        
        # Get format string
        if isinstance(format_expr, ir.ExprConstant) and isinstance(format_expr.value, str):
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

    def _is_time_call(self, expr: ir.Expr) -> bool:
        """Check if expression is self.time() which returns uint64_t."""
        if isinstance(expr, ir.ExprCall):
            func = expr.func
            if isinstance(func, ir.ExprAttribute):
                is_self = (isinstance(func.value, ir.TypeExprRefSelf) or
                           (isinstance(func.value, ir.ExprConstant) and func.value.value == "self"))
                if is_self and func.attr == "time":
                    return True
        return False

    def _gen_constant(self, expr: ir.ExprConstant) -> str:
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

    def _gen_attribute(self, expr: ir.ExprAttribute) -> str:
        """Generate C code for attribute access."""
        # Special case for TypeExprRefSelf -> access via locals->self
        if isinstance(expr.value, ir.TypeExprRefSelf):
            return f"locals->self->{expr.attr}"
        value = self._gen_expr(expr.value)
        if value == "self" or value == "locals->self":
            return f"locals->self->{expr.attr}"
        return f"{value}->{expr.attr}"

    def _gen_binop(self, expr: ir.ExprBin) -> str:
        """Generate C code for a binary operation."""
        left = self._gen_expr(expr.lhs)
        right = self._gen_expr(expr.rhs)
        op = self._get_binop_str(expr.op)
        return f"({left} {op} {right})"

    def _get_binop_str(self, op: ir.BinOp) -> str:
        """Get C operator string for binary operation."""
        op_map = {
            ir.BinOp.Add: "+",
            ir.BinOp.Sub: "-",
            ir.BinOp.Mult: "*",
            ir.BinOp.Div: "/",
            ir.BinOp.Mod: "%",
            ir.BinOp.LShift: "<<",
            ir.BinOp.RShift: ">>",
            ir.BinOp.BitOr: "|",
            ir.BinOp.BitXor: "^",
            ir.BinOp.BitAnd: "&",
        }
        return op_map.get(op, "?")

    def _gen_await_code(self, await_expr: ir.ExprAwait, await_stmt: Optional[ir.Stmt] = None) -> str:
        """Generate C code for an await expression."""
        awaited = await_expr.value
        
        # Check what we're awaiting
        if isinstance(awaited, ir.ExprCall):
            func = awaited.func
            if isinstance(func, ir.ExprAttribute):
                # Check for self.method() calls
                is_self = (isinstance(func.value, ir.TypeExprRefSelf) or
                           (isinstance(func.value, ir.ExprConstant) and func.value.value == "self"))
                if is_self:
                    if func.attr == "wait":
                        # await self.wait(time) -> zsp_timebase_wait(thread, time)
                        # Returns expression (not statement) for optimization check
                        args = awaited.args
                        if args:
                            time_arg = self._gen_time_expr(args[0])
                            return f"zsp_timebase_wait(thread, {time_arg})"
                    else:
                        # await self.other_async_method() -> call to generated task function
                        method_name = func.attr
                        task_func = f"{self.component_name}_{method_name}_task"
                        # Build argument list for the call
                        arg_list = ["locals->self"]
                        for arg in awaited.args:
                            arg_code = self._gen_expr(arg)
                            arg_list.append(arg_code)
                        args_str = ", ".join(arg_list)
                        return f"ret = zsp_timebase_call(thread, &{task_func}, {args_str});"
                
                # Check for port.put() or port.get() - TLM channel operations
                if isinstance(func.value, ir.ExprRefField):
                    # Get field info
                    field_idx = func.value.index
                    if self.component and field_idx < len(self.component.fields):
                        field = self.component.fields[field_idx]
                        if field.kind == ir.FieldKind.Port:
                            if func.attr == "put":
                                # await self.port.put(data) -> channel put via call
                                port_code = self._gen_field_ref(func.value)
                                args = awaited.args
                                if args:
                                    data_arg = self._gen_expr(args[0])
                                    return f"ret = zsp_timebase_call(thread, &zsp_channel_put_task, (zsp_channel_t *){port_code}, (uintptr_t){data_arg});"
                            elif func.attr == "get":
                                # await self.port.get() -> channel get via call
                                port_code = self._gen_field_ref(func.value)
                                return f"ret = zsp_timebase_call(thread, &zsp_channel_get_task, (zsp_channel_t *){port_code});"
        
        # Unsupported await expression - provide helpful error
        awaited_type = type(awaited).__name__
        if isinstance(awaited, ir.ExprCall):
            if isinstance(awaited.func, ir.ExprAttribute):
                method_info = f"{awaited.func.attr}()"
            else:
                method_info = f"{awaited_type}"
            raise ValueError(
                f"Unsupported await expression in '{self.method_name}': await {method_info}. "
                f"Supported: await self.wait(time), await port.put(data), await port.get(). "
                f"For other async operations, ensure they are TLM channel operations on ports."
            )
        
        raise ValueError(
            f"Unsupported await expression in '{self.method_name}': {awaited_type}. "
            f"Await must be used with self.wait(), port.put(), or port.get()."
        )

    def _is_wait_call(self, await_expr: ir.ExprAwait) -> bool:
        """Check if await expression is a wait() call."""
        awaited = await_expr.value
        if isinstance(awaited, ir.ExprCall):
            func = awaited.func
            if isinstance(func, ir.ExprAttribute):
                is_self = (isinstance(func.value, ir.TypeExprRefSelf) or
                           (isinstance(func.value, ir.ExprConstant) and func.value.value == "self"))
                return is_self and func.attr == "wait"
        return False

    def _is_channel_port(self, expr) -> bool:
        """Check if expression refers to a channel port (PutIF or GetIF)."""
        if isinstance(expr, ir.ExprRefField):
            if self.component and expr.index < len(self.component.fields):
                field = self.component.fields[expr.index]
                dtype = field.datatype
                return isinstance(dtype, (ir.DataTypePutIF, ir.DataTypeGetIF))
        return False

    def _needs_timebase(self, func: ir.Function) -> bool:
        def walk_expr(e):
            if isinstance(e, ir.ExprCall) and isinstance(e.func, ir.ExprAttribute):
                is_self = (isinstance(e.func.value, ir.TypeExprRefSelf) or
                           (isinstance(e.func.value, ir.ExprConstant) and e.func.value.value == "self"))
                if is_self and e.func.attr == "time":
                    return True
            for v in getattr(e, '__dict__', {}).values():
                if isinstance(v, ir.Expr) and walk_expr(v):
                    return True
                if isinstance(v, list):
                    for i in v:
                        if isinstance(i, ir.Expr) and walk_expr(i):
                            return True
            return False

        for s in func.body:
            e = getattr(s, 'expr', None)
            if isinstance(e, ir.Expr) and walk_expr(e):
                return True
            v = getattr(s, 'value', None)
            if isinstance(v, ir.Expr) and walk_expr(v):
                return True
        return False

    def _is_trivial_wait_only(self, func: ir.Function) -> bool:
        if len(func.body) != 1:
            return False
        s = func.body[0]
        if not isinstance(s, ir.StmtExpr):
            return False
        if not isinstance(s.expr, ir.ExprAwait):
            return False
        awaited = s.expr.value
        if not (isinstance(awaited, ir.ExprCall) and isinstance(awaited.func, ir.ExprAttribute)):
            return False
        is_self = (isinstance(awaited.func.value, ir.TypeExprRefSelf) or
                   (isinstance(awaited.func.value, ir.ExprConstant) and awaited.func.value.value == "self"))
        if not is_self or awaited.func.attr != "wait":
            return False
        return len(awaited.args) == 1

    def _generate_trivial_wait_only(self, func: ir.Function) -> str:
        func_name = f"{self.component_name}_{self.method_name}"
        awaited = func.body[0].expr.value
        time_arg = self._gen_time_expr(awaited.args[0])

        lines = []
        lines.append(f"static zsp_frame_t *{func_name}_task(")
        lines.append(f"        zsp_timebase_t *tb,")
        lines.append(f"        zsp_thread_t *thread,")
        lines.append(f"        int idx,")
        lines.append(f"        va_list *args) {{")
        lines.append(f"    zsp_frame_t *ret = thread->leaf;")
        lines.append(f"    (void)args;")
        lines.append(f"")
        lines.append(f"    switch (idx) {{")
        lines.append(f"        case 0: {{")
        lines.append(f"            /* Try fast path first - check if we can advance time without suspending */")
        lines.append(f"            uint64_t delay_ticks = zsp_timebase_to_ticks(tb, {time_arg});")
        lines.append(f"            uint64_t target_time = tb->current_time + delay_ticks;")
        lines.append(f"            int has_ready = (tb->ready_head != NULL);")
        lines.append(f"            int has_earlier_events = (tb->event_count > 0 && tb->events[0].wake_time <= target_time);")
        lines.append(f"            if (!has_ready && !has_earlier_events) {{")
        lines.append(f"                /* Fast path: advance time and return immediately without frame allocation */")
        lines.append(f"                tb->current_time = target_time;")
        lines.append(f"                return thread->leaf;  /* No state change needed */")
        lines.append(f"            }}")
        lines.append(f"            /* Slow path: must suspend, allocate frame */")
        lines.append(f"            ret = zsp_timebase_alloc_frame(thread, 0, &{func_name}_task);")
        lines.append(f"            ret->idx = 1;")
        lines.append(f"            zsp_timebase_wait(thread, {time_arg});")
        lines.append(f"            break;")
        lines.append(f"        }}")
        lines.append(f"        case 1: {{")
        lines.append(f"            ret = zsp_timebase_return(thread, 0);")
        lines.append(f"            break;")
        lines.append(f"        }}")
        lines.append(f"    }}")
        lines.append(f"    return ret;")
        lines.append(f"}}")
        lines.append(f"")

        lines.append(f"void {func_name}({self.component_name} *self, zsp_timebase_t *tb) {{")
        lines.append(f"    zsp_thread_t *thread = zsp_timebase_thread_create(")
        lines.append(f"        tb, &{func_name}_task, ZSP_THREAD_FLAGS_NONE, self);")
        lines.append(f"    thread->exit_f = (zsp_thread_exit_f)&zsp_timebase_thread_free;")
        lines.append(f"}}")

        return "\n".join(lines)

    def _gen_time_expr(self, expr: ir.Expr) -> str:
        """Generate C code for a time expression (e.g., zdc.Time.ns(1))."""
        if isinstance(expr, ir.ExprCall):
            func = expr.func
            if isinstance(func, ir.ExprAttribute):
                # Look for Time.ns(), Time.us(), etc.
                if isinstance(func.value, ir.ExprAttribute):
                    # zdc.Time.ns(1)
                    time_class = func.value
                    if time_class.attr == "Time":
                        unit = func.attr  # ns, us, ms, etc.
                        if expr.args:
                            amount = self._gen_expr(expr.args[0])
                            return f"ZSP_TIME_{unit.upper()}({amount})"
                elif isinstance(func.value, ir.ExprConstant):
                    # Time.ns(1)
                    if func.value.value == "Time":
                        unit = func.attr
                        if expr.args:
                            amount = self._gen_expr(expr.args[0])
                            return f"ZSP_TIME_{unit.upper()}({amount})"
        
        # Fallback - use expression generator
        return self._gen_expr(expr)

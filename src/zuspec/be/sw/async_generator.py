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
Async method code generation - transforms Python async methods into C coroutines.

This module converts Python async methods with await expressions into C coroutine
functions using the switch/case pattern used by the zsp_timebase runtime.
"""
import ast
from typing import List, Tuple, Set, Optional
from dataclasses import dataclass, field

from .expr_generator import ExprGenerator
from .stmt_generator import StmtGenerator


@dataclass
class AwaitPoint:
    """Represents a point where execution suspends."""
    case_idx: int
    await_expr: ast.Await
    # Statements to execute before the await
    pre_stmts: List[ast.stmt] = field(default_factory=list)


class AsyncMethodGenerator:
    """
    Generates C coroutine code from Python async methods.
    
    Transforms async methods into switch/case based coroutines that work
    with the zsp_timebase scheduling system.
    """

    def __init__(self, component_name: str, method_name: str):
        self.component_name = component_name
        self.method_name = method_name
        self.expr_gen = ExprGenerator()
        self.stmt_gen = StmtGenerator()
        self.indent_str = "    "

    def generate(self, func_def: ast.AsyncFunctionDef) -> str:
        """Generate C coroutine function from async method definition."""
        # Analyze the method to find await points
        blocks = self._split_at_awaits(func_def.body)
        
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
        lines.append(f"")
        
        # Generate locals struct if needed
        locals_struct = self._generate_locals_struct(func_def)
        if locals_struct:
            lines.append(locals_struct)
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
                lines.append(f"            /* Extract component pointer from args */")
                lines.append(f"            if (args) {{")
                lines.append(f"                locals->self = ({self.component_name} *)va_arg(*args, void *);")
                lines.append(f"            }}")
            else:
                lines.append(f"            locals_t *locals = zsp_frame_locals(ret, locals_t);")
            
            # Generate statements in this block
            block_stmts, await_expr = block
            for stmt in block_stmts:
                stmt_code = self._gen_stmt_for_coroutine(stmt)
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

    def _split_at_awaits(self, stmts: List[ast.stmt]) -> List[Tuple[List[ast.stmt], Optional[ast.Await]]]:
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

    def _find_await(self, stmt: ast.stmt) -> Optional[ast.Await]:
        """Find await expression in a statement, if any."""
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await):
            return stmt.value
        # Could extend to handle await in assignments, etc.
        return None

    def _generate_locals_struct(self, func_def: ast.AsyncFunctionDef) -> str:
        """Generate locals struct for variables that span await points."""
        lines = []
        lines.append(f"    typedef struct {{")
        lines.append(f"        {self.component_name} *self;")
        # Could analyze for additional local variables here
        lines.append(f"    }} locals_t;")
        return "\n".join(lines)

    def _gen_stmt_for_coroutine(self, stmt: ast.stmt) -> str:
        """Generate C code for a statement in coroutine context."""
        # Handle special cases first
        if isinstance(stmt, ast.Expr):
            code = self._gen_expr_for_coroutine(stmt.value)
            return f"{code};"
        
        # Use existing stmt generator for other statements
        self.stmt_gen.indent_level = 0
        code = self.stmt_gen._gen_stmt(stmt)
        # Replace self-> with locals->self->
        code = code.replace("self->", "locals->self->")
        return code

    def _gen_expr_for_coroutine(self, expr: ast.expr) -> str:
        """Generate C code for an expression in coroutine context."""
        if isinstance(expr, ast.Call):
            return self._gen_call_for_coroutine(expr)
        else:
            code = self.expr_gen.generate(expr)
            code = code.replace("self->", "locals->self->")
            return code

    def _gen_call_for_coroutine(self, call: ast.Call) -> str:
        """Generate C code for a call expression in coroutine context."""
        func = call.func
        
        # Check for self.time() and self.wait()
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "self":
                if func.attr == "time":
                    # self.time() -> zsp_timebase_current_ticks(tb)
                    return "zsp_timebase_current_ticks(tb)"
                elif func.attr == "wait":
                    # self.wait() should be in await, but handle it
                    return "/* self.wait() should be used with await */"
        
        # Check for print with format string
        if isinstance(func, ast.Name) and func.id == "print":
            return self._gen_print_for_coroutine(call.args)
        
        # Default - use expr_gen but fix self->
        code = self.expr_gen.generate(call)
        code = code.replace("self->", "locals->self->")
        return code

    def _gen_print_for_coroutine(self, args: list) -> str:
        """Generate fprintf for print() in coroutine context."""
        if not args:
            return 'fprintf(stdout, "\\n")'
        
        arg = args[0]
        
        # Check for format string: print("format %s" % value)
        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
            return self._gen_print_format_for_coroutine(arg)
        
        # Simple argument
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            escaped = arg.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'fprintf(stdout, "{escaped}\\n")'
        
        code = self._gen_expr_for_coroutine(arg)
        return f'fprintf(stdout, "%s\\n", {code})'

    def _gen_print_format_for_coroutine(self, binop: ast.BinOp) -> str:
        """Generate fprintf for print("format" % value) in coroutine context."""
        format_expr = binop.left
        value_expr = binop.right
        
        if isinstance(format_expr, ast.Constant) and isinstance(format_expr.value, str):
            format_str = format_expr.value
            value_code = self._gen_expr_for_coroutine(value_expr)
            
            # If value is self.time() (returns uint64_t), convert %s to %llu
            if self._is_time_call_ast(value_expr):
                format_str = format_str.replace('%s', '%llu')
                value_code = f"(unsigned long long){value_code}"
            
            format_str = format_str.replace('\\', '\\\\').replace('"', '\\"')
            return f'fprintf(stdout, "{format_str}\\n", {value_code})'
        
        # Fallback
        format_code = self._gen_expr_for_coroutine(format_expr)
        value_code = self._gen_expr_for_coroutine(value_expr)
        return f'fprintf(stdout, "%s\\n", {format_code}, {value_code})'

    def _is_time_call_ast(self, expr: ast.expr) -> bool:
        """Check if AST expression is self.time() which returns uint64_t."""
        if isinstance(expr, ast.Call):
            func = expr.func
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name) and func.value.id == "self":
                    if func.attr == "time":
                        return True
        return False


    def _gen_await_code(self, await_expr: ast.Await) -> str:
        """Generate C code for an await expression."""
        awaited = await_expr.value
        
        # Check what we're awaiting
        if isinstance(awaited, ast.Call):
            func = awaited.func
            if isinstance(func, ast.Attribute):
                # Check for self.wait()
                if isinstance(func.value, ast.Name) and func.value.id == "self":
                    if func.attr == "wait":
                        # await self.wait(time) -> zsp_timebase_wait(thread, time)
                        args = awaited.args
                        if args:
                            time_arg = self._gen_time_expr(args[0])
                            return f"zsp_timebase_wait(thread, {time_arg});"
        
        # Generic await - treat as yield
        return "zsp_timebase_yield(thread);"

    def _gen_time_expr(self, expr: ast.expr) -> str:
        """Generate C code for a time expression (e.g., zdc.Time.ns(1))."""
        if isinstance(expr, ast.Call):
            func = expr.func
            if isinstance(func, ast.Attribute):
                # Look for Time.ns(), Time.us(), etc.
                if isinstance(func.value, ast.Attribute):
                    # zdc.Time.ns(1)
                    time_class = func.value
                    if time_class.attr == "Time":
                        unit = func.attr  # ns, us, ms, etc.
                        if expr.args:
                            amount = self.expr_gen.generate(expr.args[0])
                            return f"ZSP_TIME_{unit.upper()}({amount})"
                elif isinstance(func.value, ast.Name):
                    # Time.ns(1)
                    if func.value.id == "Time":
                        unit = func.attr
                        if expr.args:
                            amount = self.expr_gen.generate(expr.args[0])
                            return f"ZSP_TIME_{unit.upper()}({amount})"
        
        # Fallback - use expression generator
        return self.expr_gen.generate(expr)

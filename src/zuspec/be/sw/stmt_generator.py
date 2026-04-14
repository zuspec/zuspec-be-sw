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

    def __init__(self, component=None, ctxt=None, py_globals=None, locals_struct_names=None,
                 tlm_port_mode=False, hoisted_ports=None, devirt_map=None):
        """Initialize statement generator.
        
        Args:
            component: The ir.DataTypeComponent being generated (for field name lookup)
            ctxt: The ir.Context for type resolution
            py_globals: Python module globals dict for resolving enum/constant references
            locals_struct_names: Set of variable names that live in the coroutine locals
                struct and must be accessed as ``locals->name`` rather than a bare name.
            tlm_port_mode: When True, ProtocolPort fields are embedded by value (use ``.impl``);
                when False (default), ProtocolPort fields are pointers (use ``->self``).
            hoisted_ports: Set of method-port field names whose ``impl`` pointer has been
                hoisted into a local variable ``_{name}_impl`` before the current code block.
                When a port call is emitted for a field in this set the cached local is used
                instead of ``self->{name}.impl``.
            devirt_map: Optional dict mapping port field name → SwConnection for ports whose
                target is statically known.  When present a direct C call of the form
                ``{TargetComp}__{slot}(impl, args)`` is emitted in place of the indirect
                function-pointer call.  Populated by ``DevirtualizePass``; requires that the
                target component follow the ``{Comp}__{method}`` / ``{Comp}__{method}_task``
                naming convention for its export implementations.
        """
        self.indent_level = 0
        self.indent_str = "    "
        self.component = component
        self.ctxt = ctxt
        self.py_globals: dict = py_globals or {}
        self.locals_struct_names: set = set(locals_struct_names) if locals_struct_names else set()
        self.tlm_port_mode: bool = tlm_port_mode
        self.hoisted_ports: set = set(hoisted_ports) if hoisted_ports else set()
        self.devirt_map: dict = dict(devirt_map) if devirt_map else {}

    def _indent(self) -> str:
        """Get current indentation string."""
        return self.indent_str * self.indent_level

    # Methods for generating from datamodel statements
    def _gen_dm_stmt(self, stmt) -> str:
        """Generate C code from a datamodel statement."""
        from zuspec.dataclasses import ir
        
        if isinstance(stmt, ir.StmtExpr):
            # Skip docstring literals (standalone string expressions)
            if isinstance(stmt.expr, ir.ExprConstant) and isinstance(stmt.expr.value, str):
                return ""
            expr_code = self._gen_dm_expr(stmt.expr)
            return f"{self._indent()}{expr_code};"
        elif isinstance(stmt, ir.StmtAssign):
            targets = [self._gen_dm_expr(t) for t in stmt.targets]
            # Skip assignments with unsupported tuple LHS
            if any(t.__class__.__name__ == 'ExprTuple' for t in stmt.targets):
                value = self._gen_dm_expr(stmt.value)
                return f"{self._indent()}/* tuple unpacking not supported: ... = {value} */"
            # Handle async port call: target = await self.port.method(args)
            if isinstance(stmt.value, ir.ExprAwait):
                block = self._maybe_async_port_block(stmt.value.value, targets[0])
                if block is not None:
                    return block
            value = self._gen_dm_expr(stmt.value)
            return f"{self._indent()}{targets[0]} = {value};"
        elif isinstance(stmt, ir.StmtAugAssign):
            target = self._gen_dm_expr(stmt.target)
            value = self._gen_dm_expr(stmt.value)
            op = self._get_dm_augop(stmt.op)
            return f"{self._indent()}{target} {op}= {value};"
        elif isinstance(stmt, ir.StmtReturn):
            if stmt.value:
                value = self._gen_dm_expr(stmt.value)
                return f"{self._indent()}return {value};"
            return f"{self._indent()}return;"
        elif isinstance(stmt, ir.StmtPass):
            return f"{self._indent()}/* pass */"
        elif isinstance(stmt, ir.StmtFor):
            return self._gen_dm_for(stmt)
        elif isinstance(stmt, ir.StmtIf):
            return self._gen_dm_if(stmt)
        elif isinstance(stmt, ir.StmtWhile):
            return self._gen_dm_while(stmt)
        elif isinstance(stmt, ir.StmtBreak):
            return f"{self._indent()}break;"
        elif isinstance(stmt, ir.StmtContinue):
            return f"{self._indent()}continue;"
        elif isinstance(stmt, ir.StmtAnnAssign):
            # ``target: Type = value`` — emit as assignment when value is present.
            # The variable declaration itself is handled by _collect_unresolved_names.
            if stmt.value is not None:
                target = self._gen_dm_expr(stmt.target)
                if isinstance(stmt.value, ir.ExprAwait):
                    block = self._maybe_async_port_block(stmt.value.value, target)
                    if block is not None:
                        return block
                value = self._gen_dm_expr(stmt.value)
                return f"{self._indent()}{target} = {value};"
            return ""
        elif isinstance(stmt, ir.StmtMatch):
            return self._gen_dm_match(stmt)
        else:
            return f"{self._indent()}/* unsupported dm stmt: {type(stmt).__name__} */"

    def _gen_dm_expr(self, expr) -> str:
        """Generate C code from a datamodel expression."""
        from zuspec.dataclasses import ir
        
        if isinstance(expr, ir.ExprConstant):
            return self._gen_dm_constant(expr)
        elif isinstance(expr, ir.ExprCall):
            return self._gen_dm_call(expr)
        elif isinstance(expr, ir.TypeExprRefSelf):
            return "self"
        elif isinstance(expr, ir.ExprRefField):
            return self._gen_dm_field_ref(expr)
        elif isinstance(expr, ir.ExprRefParam):
            # In coroutine context, params live in the locals struct
            if expr.name in self.locals_struct_names:
                return f"locals->{expr.name}"
            return expr.name
        elif isinstance(expr, ir.ExprRefLocal):
            if expr.name in self.locals_struct_names:
                return f"locals->{expr.name}"
            return expr.name
        elif isinstance(expr, ir.ExprRefUnresolved):
            return expr.name
        elif isinstance(expr, ir.ExprAttribute):
            value = self._gen_dm_expr(expr.value)
            if isinstance(expr.value, ir.TypeExprRefSelf):
                return f"{value}->{expr.attr}"
            elif isinstance(expr.value, ir.ExprRefField):
                return f"{value}.{expr.attr}"
            elif isinstance(expr.value, ir.ExprRefLocal):
                # locals->fn  is already a struct embedded by value, so use '.'
                return f"{value}.{expr.attr}"
            # Try to resolve as a Python class/enum attribute (e.g. AluOp.ADD → 0)
            if isinstance(expr.value, ir.ExprRefUnresolved):
                py_obj = self.py_globals.get(expr.value.name)
                if py_obj is not None:
                    resolved = getattr(py_obj, expr.attr, None)
                    if resolved is not None and isinstance(resolved, int):
                        return str(int(resolved))
            return f"{value}->{expr.attr}"
        elif isinstance(expr, ir.ExprBin):
            left = self._gen_dm_expr(expr.lhs)
            right = self._gen_dm_expr(expr.rhs)
            op = self._get_dm_binop(expr.op)
            return f"({left} {op} {right})"
        elif isinstance(expr, ir.ExprUnary):
            operand = self._gen_dm_expr(expr.operand)
            op = self._get_dm_unaryop(expr.op)
            return f"({op}{operand})"
        elif isinstance(expr, ir.ExprCompare):
            left = self._gen_dm_expr(expr.left)
            parts = [left]
            for op, comp in zip(expr.ops, expr.comparators):
                c_op = self._get_dm_cmpop(op)
                right = self._gen_dm_expr(comp)
                parts.append(f"{c_op} {right}")
            return " ".join(parts)
        elif isinstance(expr, ir.ExprBool):
            values = [self._gen_dm_expr(v) for v in expr.values]
            op = " && " if expr.op == ir.BoolOp.And else " || "
            return "(" + op.join(values) + ")"
        elif isinstance(expr, ir.ExprAwait):
            return self._gen_dm_expr(expr.value)
        elif isinstance(expr, ir.ExprSubscript):
            value = self._gen_dm_expr(expr.value)
            slice_expr = self._gen_dm_expr(expr.slice)
            return f"{value}[{slice_expr}]"
        elif isinstance(expr, ir.ExprIfExp):
            test = self._gen_dm_expr(expr.test)
            body = self._gen_dm_expr(expr.body)
            orelse = self._gen_dm_expr(expr.orelse)
            return f"({test} ? {body} : {orelse})"
        else:
            if hasattr(expr, '__class__') and expr.__class__.__name__ == 'ExprTuple':
                return "0 /* unsupported tuple */"
            return f"/* unsupported dm expr: {type(expr).__name__} */"

    def _gen_dm_field_ref(self, expr) -> str:
        """Generate C code for a field reference (ExprRefField)."""
        from zuspec.dataclasses import ir
        
        base = self._gen_dm_expr(expr.base)
        index = expr.index
        
        # Get field name from component's field list
        field_name = self._get_field_name_by_index(expr.base, index)
        
        # Determine accessor based on base type
        if isinstance(expr.base, ir.TypeExprRefSelf):
            return f"{base}->{field_name}"
        else:
            # Nested field access - need to determine type of base
            return f"{base}.{field_name}"

    def _get_field_name_by_index(self, base_expr, index: int) -> str:
        """Get field name from index, resolving through the type chain."""
        from zuspec.dataclasses import ir
        
        if isinstance(base_expr, ir.TypeExprRefSelf):
            # Direct field of current component
            if self.component and index < len(self.component.fields):
                return self.component.fields[index].name
        elif isinstance(base_expr, ir.ExprRefField):
            # Nested field - need to resolve the type of the base field
            base_type = self._get_field_type(base_expr)
            if base_type and isinstance(base_type, ir.DataTypeComponent):
                if index < len(base_type.fields):
                    return base_type.fields[index].name
            elif base_type and isinstance(base_type, ir.DataTypeRef) and self.ctxt:
                resolved = self.ctxt.type_m.get(base_type.ref_name)
                if resolved and isinstance(resolved, ir.DataTypeComponent):
                    if index < len(resolved.fields):
                        return resolved.fields[index].name
        
        # Fallback to index-based name
        return f"field_{index}"

    def _get_field_type(self, expr):
        """Get the datatype of a field expression."""
        from zuspec.dataclasses import ir

        if isinstance(expr, ir.ExprRefField):
            base_type = self._get_field_type(expr.base) if not isinstance(expr.base, ir.TypeExprRefSelf) else None

            if isinstance(expr.base, ir.TypeExprRefSelf):
                # Direct field of component
                if self.component and expr.index < len(self.component.fields):
                    dtype = self.component.fields[expr.index].datatype
                    # Resolve references
                    if isinstance(dtype, ir.DataTypeRef) and self.ctxt:
                        return self.ctxt.type_m.get(dtype.ref_name)
                    # ClaimPool[ElemType] → resolve to the element DataTypeComponent
                    if isinstance(dtype, ir.DataTypeClaimPool) and self.ctxt:
                        return self.ctxt.type_m.get(dtype.elem_type_name)
                    return dtype
            elif base_type:
                # Nested field
                if isinstance(base_type, ir.DataTypeComponent):
                    if expr.index < len(base_type.fields):
                        dtype = base_type.fields[expr.index].datatype
                        if isinstance(dtype, ir.DataTypeRef) and self.ctxt:
                            return self.ctxt.type_m.get(dtype.ref_name)
                        if isinstance(dtype, ir.DataTypeClaimPool) and self.ctxt:
                            return self.ctxt.type_m.get(dtype.elem_type_name)
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
        from zuspec.dataclasses import ir
        
        func = expr.func
        args = [self._gen_dm_expr(arg) for arg in expr.args]

        # Detect zdc.Action double-call pattern: ActionClass(inputs)(comp=self)
        # In the IR this appears as ExprCall(func=ExprCall(func=ExprRefUnresolved(name), ...), ...)
        # Action calls are now inlined at the factory level; if we reach here it means
        # the action class wasn't resolved — emit a warning comment.
        if isinstance(func, ir.ExprCall):
            return "0  /* unresolved zdc.Action call */"
        
        # Handle print() builtin - can be ExprConstant or ExprRefUnresolved
        if isinstance(func, ir.ExprConstant) and func.value == "print":
            return self._gen_dm_print(expr.args)
        if isinstance(func, ir.ExprRefUnresolved) and func.name == "print":
            return self._gen_dm_print(expr.args)
        
        # Handle range() builtin
        if isinstance(func, ir.ExprRefUnresolved) and func.name == "range":
            # range() is handled at statement level for for-loops
            args_str = ', '.join(args)
            return f"range({args_str})"

        # Handle Python builtins that map to C casts
        if isinstance(func, ir.ExprRefUnresolved):
            _cast_map = {"int": "int", "bool": "int"}
            if func.name in _cast_map and len(args) == 1:
                return f"(({_cast_map[func.name]})({args[0]}))"
            # _s32(v) = signed 32-bit reinterpret
            if func.name == "_s32" and len(args) == 1:
                return f"((int32_t)(uint32_t)({args[0]}))"
            # _sdiv32_trunc(d, v) emitted as C helper call - declare at top of emit
            if func.name == "_sdiv32_trunc" and len(args) == 2:
                return f"_sdiv32_trunc({args[0]}, {args[1]})"

        # Handle zdc.uN() / zdc.iN() type coercions: zdc.u32(x) -> (uint32_t)(x)
        if isinstance(func, ir.ExprAttribute) and isinstance(func.value, ir.ExprRefUnresolved):
            if func.value.name == "zdc" and len(args) == 1:
                attr = func.attr
                _zdc_cast_map = {
                    "u8": "uint8_t", "u16": "uint16_t",
                    "u32": "uint32_t", "u64": "uint64_t",
                    "i8": "int8_t", "i16": "int16_t",
                    "i32": "int32_t", "i64": "int64_t",
                    "bit1": "uint8_t", "bit8": "uint8_t",
                    "bit16": "uint16_t", "bit32": "uint32_t",
                    "bit64": "uint64_t",
                    # Also accept full C type names used by generated cast calls
                    "uint8_t": "uint8_t", "uint16_t": "uint16_t",
                    "uint32_t": "uint32_t", "uint64_t": "uint64_t",
                    "int8_t": "int8_t", "int16_t": "int16_t",
                    "int32_t": "int32_t", "int64_t": "int64_t",
                }
                if attr in _zdc_cast_map:
                    return f"(({_zdc_cast_map[attr]})({args[0]}))"

        # Handle method calls
        if isinstance(func, ir.ExprAttribute):
            # Check for self.method() - direct method call on component
            if isinstance(func.value, ir.TypeExprRefSelf):
                # Check if this is a callable port field (e.g. self.icache(pc))
                if self._is_callable_port(func.attr):
                    args_str = ", ".join(args)
                    sep = ", " if args_str else ""
                    return f"self->{func.attr}(self->{func.attr}_ud{sep}{args_str})"
                # Other self.method() calls not yet lowered
                return f"/* self.{func.attr}({', '.join(args)}) - direct method call */"
            
            # Check for self.field.method() - could be port call or memory access
            if isinstance(func.value, ir.ExprRefField):
                # This is a call through a field - check if it's a port or memory
                field_type = self._get_field_type(func.value)
                base_code = self._gen_dm_expr(func.value)
                
                if self._is_port_type(func.value):
                    field_kind = self._get_field_kind(func.value)
                    if field_kind == ir.FieldKind.ProtocolPort and self.tlm_port_mode:
                        # TLM method port: embedded by value, uses '.impl'.
                        # If the impl pointer was hoisted by the caller use the cached local.
                        field_name = self._get_field_name(func.value)
                        impl_expr = (f"_{field_name}_impl"
                                     if field_name and field_name in self.hoisted_ports
                                     else f"{base_code}.impl")
                        # Devirtualized sync call: emit a direct C function call instead of
                        # the indirect slot pointer, enabling compiler inlining/analysis.
                        direct = self._devirt_direct_fn(field_name, func.attr, is_async=False)
                        if direct:
                            args_str = (", " + ", ".join(args)) if args else ""
                            return f"{direct}({impl_expr}{args_str})"
                        return f"{base_code}.{func.attr}({impl_expr}, {', '.join(args)})"
                    else:
                        # Old-style Port (pointer field), uses '->self'
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
                elif isinstance(field_type, ir.DataTypeComponent):
                    # Embedded component field — check if method is a callable port
                    # e.g. self->alu_pool.execute(self->alu_pool.execute_ud, ...)
                    comp_fields = {f.name: f for f in field_type.fields}
                    if func.attr in comp_fields and comp_fields[func.attr].kind == ir.FieldKind.CallablePort:
                        args_str = ", ".join(args)
                        sep = ", " if args_str else ""
                        return f"{base_code}.{func.attr}({base_code}.{func.attr}_ud{sep}{args_str})"
                    # Check if it's a process/function on the component type
                    # (emitted as a standalone C function: TypeName_method(&field, args))
                    comp_funcs = {f.name: f for f in (field_type.functions or [])}
                    if func.attr in comp_funcs:
                        args_str = ", ".join(args)
                        sep = ", " if args_str else ""
                        type_name = field_type.name or "Comp"
                        return f"{type_name}_{func.attr}(&{base_code}{sep}{args_str})"
                    # Unknown method on embedded component
                    return f"{base_code}.{func.attr}({', '.join(args)})"
                else:
                    # Regular field method call
                    return f"{base_code}.{func.attr}({', '.join(args)})"
            
            # Generic attribute call
            value = self._gen_dm_expr(func.value)
            return f"{value}->{func.attr}({', '.join(args)})"
        
        # Handle field-ref calls: ExprRefField(base=TypeExprRefSelf, index=N) means
        # the func is a direct component field (e.g. self.icache).  For callable
        # ports this must be invoked with the _ud pointer prepended.
        if isinstance(func, ir.ExprRefField) and isinstance(func.base, ir.TypeExprRefSelf):
            if self.component and func.index < len(self.component.fields):
                field = self.component.fields[func.index]
                if field.kind == ir.FieldKind.CallablePort:
                    args_str = ", ".join(args)
                    sep = ", " if args_str else ""
                    return f"self->{field.name}(self->{field.name}_ud{sep}{args_str})"

        func_name = self._gen_dm_expr(func)
        return f"{func_name}({', '.join(args)})"

    def _maybe_async_port_block(self, call_expr, target_code: str) -> "Optional[str]":
        """Generate an LT-mode block for ``target = await port.method(args)``.

        Only applies to ProtocolPort fields (TLM method ports embedded by value).
        For async method ports the slot signature is:
            struct zsp_frame_s *(*method)(void *impl, zsp_thread_t *thread, ..., zsp_frame_t **ret_pp)
        In LT mode the callee accumulates time and returns NULL (no real suspension).
        The caller picks up the return value from ``thread->rval``.

        Returns the block string, or None if *call_expr* is not an async protocol port call.
        """
        from zuspec.dataclasses import ir
        if not isinstance(call_expr, ir.ExprCall):
            return None
        func = call_expr.func
        if not isinstance(func, ir.ExprAttribute):
            return None
        if not isinstance(func.value, ir.ExprRefField):
            return None
        if self._get_field_kind(func.value) != ir.FieldKind.ProtocolPort or not self.tlm_port_mode:
            return None
        base = self._gen_dm_expr(func.value)
        field_name = self._get_field_name(func.value)
        impl_expr = (f"_{field_name}_impl"
                     if field_name and field_name in self.hoisted_ports
                     else f"{base}.impl")
        args = [self._gen_dm_expr(a) for a in call_expr.args]
        args_str = (", " + ", ".join(args)) if args else ""
        ind = self._indent()
        # Devirtualized async call: emit a direct C function call when the target is
        # statically known, eliminating the indirect slot pointer dereference.
        direct = self._devirt_direct_fn(field_name, func.attr, is_async=True)
        if direct:
            call_stmt = f"{direct}({impl_expr}, thread{args_str}, &_pr);"
        else:
            call_stmt = f"{base}.{func.attr}({impl_expr}, thread{args_str}, &_pr);"
        lines = [
            f"{ind}{{",
            f"{ind}    struct zsp_frame_s *_pr = NULL;",
            f"{ind}    {call_stmt}",
            f"{ind}    {target_code} = (uint64_t)thread->rval;",
            f"{ind}}}",
        ]
        return "\n".join(lines)

    def _get_field_kind(self, expr) -> "Optional[ir.FieldKind]":
        """Return the FieldKind for an ExprRefField pointing to a direct component field, or None."""
        from zuspec.dataclasses import ir
        if isinstance(expr, ir.ExprRefField) and isinstance(expr.base, ir.TypeExprRefSelf):
            if self.component and expr.index < len(self.component.fields):
                return self.component.fields[expr.index].kind
        return None

    def _get_field_name(self, expr) -> "Optional[str]":
        """Return the field name for an ExprRefField pointing to a direct component field, or None."""
        from zuspec.dataclasses import ir
        if isinstance(expr, ir.ExprRefField) and isinstance(expr.base, ir.TypeExprRefSelf):
            if self.component and expr.index < len(self.component.fields):
                return self.component.fields[expr.index].name
        return None

    def _devirt_direct_fn(self, field_name: "Optional[str]", slot: str, is_async: bool) -> "Optional[str]":
        """Return the direct C function name for a devirtualized port call, or None.

        When the target implementation is statically known (``devirt_map`` contains
        an entry for *field_name*), we can call the concrete function directly instead
        of going through the function-pointer slot.  The naming convention is:

        * Sync slot: ``{TargetComp}__{slot}``  e.g. ``DramModel__read``
        * Async slot: ``{TargetComp}__{slot}_task``  e.g. ``DramModel__fetch_task``

        Returns None when devirtualization is not possible (no entry, or field_name
        is None).  Callers fall back to the indirect slot call in that case.
        """
        if not field_name or field_name not in self.devirt_map:
            return None
        conn = self.devirt_map[field_name]
        target = conn.target_component
        if not target:
            return None
        suffix = f"_task" if is_async else ""
        return f"{target}__{slot}{suffix}"

    def _is_port_type(self, expr) -> bool:
        """Check if an expression refers to a port field."""
        from zuspec.dataclasses import ir
        _port_kinds = (ir.FieldKind.Port, ir.FieldKind.ProtocolPort, ir.FieldKind.CallablePort)
        if isinstance(expr, ir.ExprRefField):
            if isinstance(expr.base, ir.TypeExprRefSelf):
                # Direct field of component
                if self.component and expr.index < len(self.component.fields):
                    return self.component.fields[expr.index].kind in _port_kinds
        return False

    def _is_callable_port(self, attr: str) -> bool:
        """Return True if *attr* is the name of a CallablePort field on the component."""
        from zuspec.dataclasses import ir
        if self.component is None:
            return False
        for field in self.component.fields:
            if field.name == attr and field.kind == ir.FieldKind.CallablePort:
                return True
        return False

    def _is_memory_type(self, expr) -> bool:
        """Check if an expression refers to a memory field."""
        from zuspec.dataclasses import ir
        
        if isinstance(expr, ir.ExprRefField):
            field_type = self._get_field_type(expr)
            return isinstance(field_type, ir.DataTypeMemory)
        return False

    def _gen_dm_print(self, args) -> str:
        """Generate fprintf for print()."""
        from zuspec.dataclasses import ir
        
        if not args:
            return 'fprintf(stdout, "\\n")'
        
        arg = args[0]
        
        # Check for format string
        if isinstance(arg, ir.ExprBin) and arg.op == ir.BinOp.Mod:
            format_expr = arg.lhs
            value_expr = arg.rhs
            if isinstance(format_expr, ir.ExprConstant) and isinstance(format_expr.value, str):
                format_str = format_expr.value.replace('\\', '\\\\').replace('"', '\\"')
                value_code = self._gen_dm_expr(value_expr)
                return f'fprintf(stdout, "{format_str}\\n", {value_code})'
        
        # Simple argument
        if isinstance(arg, ir.ExprConstant) and isinstance(arg.value, str):
            escaped = arg.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'fprintf(stdout, "{escaped}\\n")'
        
        arg_code = self._gen_dm_expr(arg)
        return f'fprintf(stdout, "%s\\n", {arg_code})'

    def _get_dm_binop(self, op) -> str:
        """Get C operator string for datamodel binary operation."""
        from zuspec.dataclasses import ir
        op_map = {
            ir.BinOp.Add: "+",
            ir.BinOp.Sub: "-",
            ir.BinOp.Mult: "*",
            ir.BinOp.Div: "/",
            ir.BinOp.FloorDiv: "/",
            ir.BinOp.Mod: "%",
            ir.BinOp.LShift: "<<",
            ir.BinOp.RShift: ">>",
            ir.BinOp.BitOr: "|",
            ir.BinOp.BitXor: "^",
            ir.BinOp.BitAnd: "&",
        }
        return op_map.get(op, "?")

    def _get_dm_augop(self, op) -> str:
        """Get C augmented-assignment operator (without '=') for datamodel AugOp."""
        from zuspec.dataclasses import ir
        # AugOp enum values mirror BinOp
        op_map = {
            ir.AugOp.Add: "+",
            ir.AugOp.Sub: "-",
            ir.AugOp.Mult: "*",
            ir.AugOp.Div: "/",
            ir.AugOp.Mod: "%",
            ir.AugOp.LShift: "<<",
            ir.AugOp.RShift: ">>",
            ir.AugOp.BitOr: "|",
            ir.AugOp.BitXor: "^",
            ir.AugOp.BitAnd: "&",
        }
        return op_map.get(op, "?")

    def _get_dm_cmpop(self, op) -> str:
        """Get C comparison operator for datamodel CmpOp."""
        from zuspec.dataclasses import ir
        op_map = {
            ir.CmpOp.Eq: "==",
            ir.CmpOp.NotEq: "!=",
            ir.CmpOp.Lt: "<",
            ir.CmpOp.LtE: "<=",
            ir.CmpOp.Gt: ">",
            ir.CmpOp.GtE: ">=",
        }
        return op_map.get(op, "==")

    def _get_dm_unaryop(self, op) -> str:
        """Get C unary operator for datamodel UnaryOp."""
        from zuspec.dataclasses import ir
        op_map = {
            ir.UnaryOp.Not: "!",
            ir.UnaryOp.Invert: "~",
            ir.UnaryOp.UAdd: "+",
            ir.UnaryOp.USub: "-",
        }
        return op_map.get(op, "!")

    def _gen_dm_for(self, stmt) -> str:
        """Generate C for loop from datamodel."""
        lines = []
        target = self._gen_dm_expr(stmt.target)
        
        # Check for range iteration
        iter_expr = stmt.iter
        from zuspec.dataclasses import ir
        if isinstance(iter_expr, ir.ExprCall):
            func_name = None
            if isinstance(iter_expr.func, ir.ExprConstant) and iter_expr.func.value == "range":
                func_name = "range"
            elif isinstance(iter_expr.func, ir.ExprRefUnresolved) and iter_expr.func.name == "range":
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
        # For infinite loops inject an async halt check so that
        # request_halt() (safe from ctypes callbacks) can break the loop.
        if test in ("1", "true"):
            ind = self._indent()
            lines.append(
                f"{ind}if (self->_halt_requested) {{ longjmp(self->_halt_jmp, 1); }}"
            )
        for s in stmt.body:
            lines.append(self._gen_dm_stmt(s))
        self.indent_level -= 1
        
        lines.append(f"{self._indent()}}}")
        return "\n".join(lines)

    def _gen_dm_match(self, stmt) -> str:
        """Generate C if/else chain from a StmtMatch (Python match/case).

        ``match subject: case v: body`` becomes:
        ``if (subject == v) { body } else if ... else { }``
        """
        from zuspec.dataclasses import ir

        lines = []
        subject = self._gen_dm_expr(stmt.subject)
        first = True
        for case in stmt.cases:
            pattern = case.pattern
            if isinstance(pattern, ir.PatternValue):
                cond = f"{subject} == {self._gen_dm_expr(pattern.value)}"
            elif isinstance(pattern, (ir.PatternAs,)) and pattern.pattern is None:
                # wildcard (``case _:``)
                cond = None
            else:
                cond = f"/* pattern {type(pattern).__name__} */ 1"
            # Optional guard
            if case.guard is not None:
                guard_expr = self._gen_dm_expr(case.guard)
                cond = f"({cond}) && ({guard_expr})" if cond else guard_expr

            if cond is None:
                # Wildcard / default case
                lines.append(f"{self._indent()}else {{")
            elif first:
                lines.append(f"{self._indent()}if ({cond}) {{")
                first = False
            else:
                lines.append(f"{self._indent()}else if ({cond}) {{")

            self.indent_level += 1
            for s in case.body:
                lines.append(self._gen_dm_stmt(s))
            self.indent_level -= 1
            lines.append(f"{self._indent()}}}")

        return "\n".join(lines)


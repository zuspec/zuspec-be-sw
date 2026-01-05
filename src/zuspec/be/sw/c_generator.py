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
C code generator for transforming datamodel to C source code.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Type, Any

from zuspec.dataclasses import ir

from .type_mapper import TypeMapper
from .stmt_generator import StmtGenerator
from .dm_async_generator import DmAsyncMethodGenerator
from .sync_generator import SyncMethodGenerator
from .async_analyzer import AsyncAnalyzer
from .output import OutputManager


def sanitize_c_name(name: str) -> str:
    """Sanitize a name to be a valid C identifier."""
    # Extract just the class name if it's a qualified name
    if '.' in name:
        name = name.split('.')[-1]
    # Replace any invalid characters with underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure it doesn't start with a digit
    if name and name[0].isdigit():
        name = '_' + name
    return name


class CGenerator:
    """Main C code generator from datamodel."""

    def __init__(self, output_dir: Path, enable_specialization: bool = False):
        self.output_dir = Path(output_dir)
        self.type_mapper = TypeMapper(enable_specialization=enable_specialization)
        self.output = OutputManager(output_dir)
        self.py_classes: Dict[str, Type] = {}  # Map from type name to Python class
        self.async_analyzer: Optional[AsyncAnalyzer] = None  # Async-to-sync analyzer
        self.enable_specialization = enable_specialization

    def generate(self, ctxt: ir.Context, py_classes: List[Type] = None) -> List[Path]:
        """Generate C code for all types in context.
        
        Args:
            ctxt: The datamodel context
            py_classes: Optional list of original Python classes for source introspection
        """
        # Build map of Python classes by name
        if py_classes:
            for cls in py_classes:
                self.py_classes[cls.__name__] = cls
        
        # Analyze async functions for sync conversion opportunity
        self.async_analyzer = AsyncAnalyzer(ctxt)
        self.async_analyzer.analyze()
        
        # Print analysis report if there are convertible functions
        report = self.async_analyzer.get_report()
        if report:
            print("\n" + report + "\n")
        
        # First pass: generate protocol/API types
        for name, dtype in ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeProtocol):
                self._generate_protocol(dtype, ctxt)
        
        # Second pass: generate components
        for name, dtype in ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeComponent):
                self._generate_component(dtype, ctxt)
        
        # Generate test harness
        self._generate_main(ctxt)
        
        return self.output.write_all()

    def _generate_protocol(self, proto: ir.DataTypeProtocol, ctxt: ir.Context):
        """Generate C code for a Protocol (API interface)."""
        name = sanitize_c_name(proto.name)
        
        # Generate header with API struct
        header = self._generate_protocol_header(proto, name)
        self.output.add_header(name.lower(), header)

    def _generate_protocol_header(self, proto: ir.DataTypeProtocol, name: str) -> str:
        """Generate protocol/API header file."""
        guard = f"INCLUDED_{name.upper()}_H"
        
        lines = [
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
            "#include <stdint.h>",
            "",
            f"/* {name} API interface */",
            f"typedef struct {name}_s {{",
            f"    void *self;  /* Context/this pointer */",
        ]
        
        # Add function pointers for each method
        for func in proto.methods:
            ret_type = self.type_mapper.map_type(func.returns) if func.returns else "void"
            params = self._generate_func_params(func)
            lines.append(f"    {ret_type} (*{func.name})({params});")
        
        lines.extend([
            f"}} {name}_t;",
            "",
            f"#endif /* {guard} */",
        ])
        
        return "\n".join(lines)

    def _generate_func_params(self, func: ir.Function) -> str:
        """Generate C function parameter list from function datamodel."""
        params = ["void *self"]
        
        if func.args and func.args.args:
            for arg in func.args.args:
                # Get type from annotation
                arg_type = "int32_t"  # Default type
                if arg.annotation and hasattr(arg.annotation, 'value'):
                    ann_val = arg.annotation.value
                    if hasattr(ann_val, '__name__'):
                        type_name = ann_val.__name__
                        if 'uint32' in type_name:
                            arg_type = "uint32_t"
                        elif 'int32' in type_name:
                            arg_type = "int32_t"
                        elif 'uint64' in type_name:
                            arg_type = "uint64_t"
                        elif 'int64' in type_name:
                            arg_type = "int64_t"
                params.append(f"{arg_type} {arg.arg}")
        
        return ", ".join(params)

    def _generate_component(self, comp: ir.DataTypeComponent, ctxt: ir.Context):
        """Generate C code for a component."""
        name = sanitize_c_name(comp.name)
        
        # Generate header
        header = self._generate_component_header(comp, name, ctxt)
        self.output.add_header(name.lower(), header)
        
        # Generate implementation
        impl = self._generate_component_impl(comp, name, ctxt)
        self.output.add_source(name.lower(), impl)


    def _generate_component_header(self, comp: ir.DataTypeComponent, name: str, ctxt: ir.Context) -> str:
        """Generate component header file."""
        guard = f"INCLUDED_{name.upper()}_H"
        
        # Check if we have any async methods
        has_async = any(getattr(f, 'is_async', False) 
                       for f in comp.functions 
                       if self._should_generate_method(f))
        
        # Check if we have ports/exports that need protocol headers
        protocol_includes = set()
        component_includes = set()
        has_ports_or_exports = False
        has_channels = False
        has_memories = False
        has_tlm_interfaces = False
        
        for field in comp.fields:
            if field.kind == ir.FieldKind.Port or field.kind == ir.FieldKind.Export:
                has_ports_or_exports = True
                if isinstance(field.datatype, ir.DataTypeRef):
                    protocol_includes.add(field.datatype.ref_name.lower())
                elif isinstance(field.datatype, ir.DataTypeProtocol):
                    protocol_includes.add(sanitize_c_name(field.datatype.name).lower())
                elif isinstance(field.datatype, (ir.DataTypeGetIF, ir.DataTypePutIF)):
                    has_tlm_interfaces = True
            # Check for memory fields
            if isinstance(field.datatype, ir.DataTypeMemory):
                has_memories = True
            # Check for channel fields
            elif isinstance(field.datatype, ir.DataTypeChannel):
                has_channels = True
            # Check for sub-component fields
            elif isinstance(field.datatype, ir.DataTypeComponent):
                component_includes.add(sanitize_c_name(field.datatype.name).lower())
            elif isinstance(field.datatype, ir.DataTypeRef):
                ref_type = ctxt.type_m.get(field.datatype.ref_name)
                if isinstance(ref_type, ir.DataTypeComponent):
                    component_includes.add(sanitize_c_name(field.datatype.ref_name).lower())
        
        lines = [
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
            "#include <stdio.h>",
            "#include <stdint.h>",
            "#include <string.h>",
            '#include "zsp_component.h"',
            '#include "zsp_init_ctxt.h"',
        ]
        
        if has_async:
            lines.append('#include "zsp_timebase.h"')
        
        if has_memories:
            lines.append('#include "zsp_memory.h"')
        
        if has_channels or has_tlm_interfaces:
            lines.append('#include "zsp_channel.h"')
        
        # Include protocol headers
        for proto_name in sorted(protocol_includes):
            lines.append(f'#include "{proto_name}.h"')
        
        # Include component headers for sub-components
        for comp_name in sorted(component_includes):
            lines.append(f'#include "{comp_name}.h"')
        
        lines.extend([
            "",
            f"/* Forward declaration */",
            f"struct {name};",
            "",
            f"/* {name} type definition */",
            f"typedef struct {name} {{",
            f"    zsp_component_t base;",
            f"    zsp_timebase_t *timebase;  /* Timebase for this component */",
        ])
        
        # Add fields - handle ports, exports, and sub-components specially
        for field in comp.fields:
            is_port = field.kind == ir.FieldKind.Port
            is_export = field.kind == ir.FieldKind.Export
            # Check if this is a sub-component field
            is_subcomp = False
            if isinstance(field.datatype, ir.DataTypeComponent):
                is_subcomp = True
            elif isinstance(field.datatype, ir.DataTypeRef):
                ref_type = ctxt.type_m.get(field.datatype.ref_name)
                if isinstance(ref_type, ir.DataTypeComponent):
                    is_subcomp = True
            
            # Handle specialized types (Phase 1-2: Direct memory/channel)
            if self.enable_specialization and isinstance(field.datatype, ir.DataTypeMemory):
                # Generate direct C array for memory
                type_info = self.type_mapper.get_type_info(field.datatype)
                lines.append(f"    {type_info.element_type} {field.name}_data[{type_info.size}];")
            elif self.enable_specialization and isinstance(field.datatype, ir.DataTypeChannel):
                # Generate ring buffer fields for channel
                type_info = self.type_mapper.get_type_info(field.datatype)
                lines.append(f"    {type_info.element_type} {field.name}_buffer[{type_info.capacity}];")
                lines.append(f"    uint32_t {field.name}_head;")
                lines.append(f"    uint32_t {field.name}_tail;")
                lines.append(f"    uint32_t {field.name}_count;")
            else:
                c_type = self.type_mapper.map_type(field.datatype, is_port=is_port, is_export=is_export, 
                                                   is_subcomponent=is_subcomp)
                if c_type:  # Only add if not None (None signals specialized handling)
                    lines.append(f"    {c_type} {field.name};")
        
        lines.append(f"}} {name};")
        lines.append("")
        
        # Generate inline accessors for specialized fields (Phase 3)
        if self.enable_specialization:
            for field in comp.fields:
                if isinstance(field.datatype, ir.DataTypeMemory):
                    lines.extend(self._generate_memory_accessors(name, field, field.datatype))
                    lines.append("")
                elif isinstance(field.datatype, ir.DataTypeChannel):
                    lines.extend(self._generate_channel_accessors(name, field, field.datatype))
                    lines.append("")
        
        # Function declarations
        lines.append(f"/* Initialize {name} */")
        lines.append(f"void {name}_init(")
        lines.append(f"    zsp_init_ctxt_t *ctxt,")
        lines.append(f"    {name} *self,")
        lines.append(f"    const char *name,")
        lines.append(f"    zsp_component_t *parent);")
        lines.append("")
        
        # Generate bind function declaration if component has bindings
        if comp.bind_map or has_ports_or_exports:
            lines.append(f"/* Bind ports and exports */")
            lines.append(f"void {name}__bind({name} *self);")
            lines.append("")
        
        # Method declarations
        for func in comp.functions:
            if self._should_generate_method(func):
                params = self._generate_method_params(func, name)
                if getattr(func, 'is_async', False):
                    # Check if this function can be converted to sync
                    can_be_sync = False
                    if self.async_analyzer:
                        can_be_sync = self.async_analyzer.is_sync_convertible(name, func.name)
                    
                    if can_be_sync:
                        # Declare synchronous variant (inline, in header)
                        ret_type = self._get_func_return_type(func)
                        lines.append(f"/* Synchronous variant (optimized) */")
                        lines.append(f"static inline {ret_type} {name}_{func.name}_sync({params});")
                    
                    # Async methods take a timebase parameter (always declare for compatibility)
                    lines.append(f"/* Asynchronous variant */")
                    lines.append(f"void {name}_{func.name}({params}, zsp_timebase_t *tb);")
                else:
                    ret_type = self._get_method_return_type(func)
                    lines.append(f"{ret_type} {name}_{func.name}({params});")
        
        # Comb process declarations
        if hasattr(comp, 'comb_processes') and comp.comb_processes:
            lines.append("")
            lines.append("/* Combinational processes */")
            for comb_func in comp.comb_processes:
                lines.append(f"void {name}_{comb_func.name}({name} *self);")
        
        # Sync process declarations
        if hasattr(comp, 'sync_processes') and comp.sync_processes:
            lines.append("")
            lines.append("/* Synchronous processes */")
            for sync_func in comp.sync_processes:
                lines.append(f"void {name}_{sync_func.name}({name} *self);")
        
        lines.append("")
        lines.append(f"#endif /* {guard} */")
        
        return "\n".join(lines)

    def _generate_memory_accessors(self, comp_name: str, field: ir.Field, mem_dtype: ir.DataTypeMemory) -> List[str]:
        """Generate inline memory accessor functions (Phase 3)."""
        lines = [f"/* Inline accessors for {field.name} memory */"]
        
        # Generate read accessors for different widths
        for width in [8, 16, 32, 64]:
            c_type = f"uint{width}_t"
            lines.extend([
                f"static inline {c_type} {comp_name}_{field.name}_read{width}(",
                f"    {comp_name} *self, uint64_t addr) {{",
                f"    return *({c_type} *)(self->{field.name}_data + addr);",
                f"}}",
                ""
            ])
        
        # Generate write accessors for different widths
        for width in [8, 16, 32, 64]:
            c_type = f"uint{width}_t"
            lines.extend([
                f"static inline void {comp_name}_{field.name}_write{width}(",
                f"    {comp_name} *self, uint64_t addr, {c_type} value) {{",
                f"    *({c_type} *)(self->{field.name}_data + addr) = value;",
                f"}}",
                ""
            ])
        
        return lines

    def _generate_channel_accessors(self, comp_name: str, field: ir.Field, ch_dtype: ir.DataTypeChannel) -> List[str]:
        """Generate inline channel accessor functions (Phase 3)."""
        type_info = self.type_mapper.get_type_info(ch_dtype)
        elem_type = type_info.element_type
        capacity = type_info.capacity
        mask = capacity - 1  # For power-of-2 modulo optimization
        
        lines = [f"/* Inline accessors for {field.name} channel */"]
        
        # Put operation
        lines.extend([
            f"static inline void {comp_name}_{field.name}_put(",
            f"    {comp_name} *self, {elem_type} value) {{",
            f"    self->{field.name}_buffer[self->{field.name}_tail] = value;",
            f"    self->{field.name}_tail = (self->{field.name}_tail + 1) & {mask};",
            f"    self->{field.name}_count++;",
            f"}}",
            ""
        ])
        
        # Get operation
        lines.extend([
            f"static inline {elem_type} {comp_name}_{field.name}_get(",
            f"    {comp_name} *self) {{",
            f"    {elem_type} value = self->{field.name}_buffer[self->{field.name}_head];",
            f"    self->{field.name}_head = (self->{field.name}_head + 1) & {mask};",
            f"    self->{field.name}_count--;",
            f"    return value;",
            f"}}",
            ""
        ])
        
        # Check if empty
        lines.extend([
            f"static inline int {comp_name}_{field.name}_empty(",
            f"    {comp_name} *self) {{",
            f"    return self->{field.name}_count == 0;",
            f"}}",
            ""
        ])
        
        # Check if full
        lines.extend([
            f"static inline int {comp_name}_{field.name}_full(",
            f"    {comp_name} *self) {{",
            f"    return self->{field.name}_count >= {capacity};",
            f"}}",
            ""
        ])
        
        return lines

    def _generate_component_impl(self, comp: ir.DataTypeComponent, name: str, ctxt: ir.Context) -> str:
        """Generate component implementation file."""
        
        # Collect required includes
        includes = [f'#include "{name.lower()}.h"', '#include "zsp_init_ctxt.h"']
        
        # Check for field types that need includes
        for field in comp.fields:
            if isinstance(field.datatype, ir.DataTypeComponent):
                field_name = sanitize_c_name(field.datatype.name)
                includes.append(f'#include "{field_name.lower()}.h"')
            elif isinstance(field.datatype, ir.DataTypeRef):
                # Check if this is a component reference
                ref_type = ctxt.type_m.get(field.datatype.ref_name)
                if isinstance(ref_type, ir.DataTypeComponent):
                    field_name = sanitize_c_name(field.datatype.ref_name)
                    includes.append(f'#include "{field_name.lower()}.h"')
        
        lines = list(dict.fromkeys(includes))  # Remove duplicates while preserving order
        lines.append("")
        
        # Generate init function
        lines.extend(self._generate_init_function(comp, name, ctxt))
        lines.append("")
        
        # Generate bind function if needed
        has_ports_or_exports = any(
            field.kind == ir.FieldKind.Port or field.kind == ir.FieldKind.Export
            for field in comp.fields
        )
        if comp.bind_map or has_ports_or_exports:
            lines.extend(self._generate_bind_function(comp, name, ctxt))
            lines.append("")
        
        # Generate methods
        for func in comp.functions:
            if self._should_generate_method(func):
                method_code = self._generate_method(comp, func, name, ctxt)
                lines.extend(method_code)
                lines.append("")
        
        # Generate process task wrappers and collect process list
        processes = []
        for func in comp.functions:
            if isinstance(func, ir.Process):
                processes.append(func)
                # Generate the process task wrapper
                process_code = self._generate_process_task(comp, func, name, ctxt)
                lines.extend(process_code)
                lines.append("")
        
        # Generate process startup function if there are processes
        if processes:
            startup_code = self._generate_process_startup(comp, processes, name, ctxt)
            lines.extend(startup_code)
            lines.append("")
        
        # Generate comb processes
        if hasattr(comp, 'comb_processes') and comp.comb_processes:
            for comb_func in comp.comb_processes:
                method_code = self._generate_comb_process(comp, comb_func, name, ctxt)
                lines.extend(method_code)
                lines.append("")
        
        # Generate sync processes
        if hasattr(comp, 'sync_processes') and comp.sync_processes:
            for sync_func in comp.sync_processes:
                method_code = self._generate_sync_process(comp, sync_func, name, ctxt)
                lines.extend(method_code)
                lines.append("")
        
        return "\n".join(lines)

    def _generate_init_function(self, comp: ir.DataTypeComponent, name: str, ctxt: ir.Context) -> List[str]:
        """Generate component initialization function."""
        
        lines = [
            f"void {name}_init(",
            f"    zsp_init_ctxt_t *ctxt,",
            f"    {name} *self,",
            f"    const char *name,",
            f"    zsp_component_t *parent) {{",
            f"    zsp_component_init(ctxt, &self->base, name, parent);",
            f"    self->timebase = ctxt->timebase;  /* Store timebase reference */",
        ]
        
        # Initialize fields
        for field in comp.fields:
            if field.kind == ir.FieldKind.Port:
                # Ports are pointers, initialize to NULL
                lines.append(f"    self->{field.name} = NULL;")
            elif field.kind == ir.FieldKind.Export:
                # Exports are embedded structs, zero-initialize self pointer
                lines.append(f"    self->{field.name}.self = NULL;")
            elif isinstance(field.datatype, ir.DataTypeMemory):
                if self.enable_specialization:
                    # Specialized: Initialize direct C array with memset
                    type_info = self.type_mapper.get_type_info(field.datatype)
                    lines.append(f'    memset(self->{field.name}_data, 0, sizeof(self->{field.name}_data));')
                else:
                    # Generic: call memory init with size and element width
                    size = field.datatype.size
                    elem_type = field.datatype.element_type
                    if isinstance(elem_type, ir.DataTypeInt):
                        width = elem_type.bits
                    else:
                        width = 32  # Default
                    lines.append(f'    zsp_memory_init(ctxt, &self->{field.name}, "{field.name}", &self->base, {size}, {width});')
            elif isinstance(field.datatype, ir.DataTypeChannel):
                if self.enable_specialization:
                    # Specialized: Initialize ring buffer indices
                    lines.append(f'    self->{field.name}_head = 0;')
                    lines.append(f'    self->{field.name}_tail = 0;')
                    lines.append(f'    self->{field.name}_count = 0;')
                else:
                    # Generic: call channel init with element size
                    elem_size = self.type_mapper.get_element_size(field.datatype.element_type)
                    lines.append(f'    zsp_channel_init(ctxt, &self->{field.name}, "{field.name}", &self->base, {elem_size});')
            elif isinstance(field.datatype, ir.DataTypeComponent) or \
                 (isinstance(field.datatype, ir.DataTypeRef) and 
                  isinstance(ctxt.type_m.get(field.datatype.ref_name), ir.DataTypeComponent)):
                # Sub-component: call its init function
                if isinstance(field.datatype, ir.DataTypeRef):
                    field_type_name = sanitize_c_name(field.datatype.ref_name)
                else:
                    field_type_name = sanitize_c_name(field.datatype.name)
                lines.append(f'    {field_type_name}_init(ctxt, &self->{field.name}, "{field.name}", &self->base);')
            else:
                default = self.type_mapper.get_default_value(field.datatype)
                if default:
                    lines.append(f"    self->{field.name} = {default};")
        
        lines.append("}")
        return lines

    def _generate_bind_function(self, comp: ir.DataTypeComponent, name: str, ctxt: ir.Context) -> List[str]:
        """Generate component bind function for connecting ports and exports."""
        
        lines = [
            f"void {name}__bind({name} *self) {{",
        ]
        
        # First, call bind on sub-components
        for field in comp.fields:
            if isinstance(field.datatype, ir.DataTypeComponent) or \
               (isinstance(field.datatype, ir.DataTypeRef) and 
                isinstance(ctxt.type_m.get(field.datatype.ref_name), ir.DataTypeComponent)):
                if isinstance(field.datatype, ir.DataTypeRef):
                    field_type_name = sanitize_c_name(field.datatype.ref_name)
                else:
                    field_type_name = sanitize_c_name(field.datatype.name)
                # Check if the sub-component has ports/exports
                sub_comp = ctxt.type_m.get(field.datatype.ref_name if isinstance(field.datatype, ir.DataTypeRef) else field.datatype.name)
                if sub_comp and isinstance(sub_comp, ir.DataTypeComponent):
                    has_sub_binds = any(f.kind in (ir.FieldKind.Port, ir.FieldKind.Export) for f in sub_comp.fields)
                    if has_sub_binds or sub_comp.bind_map:
                        lines.append(f"    {field_type_name}__bind(&self->{field.name});")
        
        # Process bind_map to generate port-to-export connections
        for bind in comp.bind_map:
            bind_code = self._generate_bind_statement(bind, comp, name, ctxt)
            if bind_code:
                for line in bind_code:
                    lines.append(f"    {line}")
        
        lines.append("}")
        return lines

    def _generate_bind_statement(self, bind: ir.Bind, comp: ir.DataTypeComponent, comp_name: str, ctxt: ir.Context) -> List[str]:
        """Generate C statements for a single bind operation."""
        lhs = bind.lhs
        rhs = bind.rhs
        
        # Check if this is a method binding (ExprRefPy at top level)
        if isinstance(lhs, ir.ExprRefPy):
            # Method binding: self.exp.method : self.method
            # Generates: self->exp.method = (func_ptr)CompType_method;
            return self._generate_method_bind(lhs, rhs, comp, comp_name, ctxt)
        
        # Check if RHS is a channel interface binding (self.ch.put or self.ch.get)
        if isinstance(rhs, ir.ExprRefPy):
            rhs_attr = rhs.ref
            if rhs_attr in ("put", "get"):
                # This is a channel binding: self.subcomp.port : self.ch.put/get
                return self._generate_channel_bind(lhs, rhs, comp, comp_name, ctxt)
        
        # Otherwise it's a port-to-export binding
        lhs_code = self._expr_to_c(lhs, comp, "self", ctxt)
        rhs_code = self._expr_to_c(rhs, comp, "self", ctxt)
        
        if lhs_code and rhs_code:
            return [f"{lhs_code} = &{rhs_code};"]
        
        return []

    def _generate_channel_bind(self, lhs, rhs: ir.ExprRefPy, comp: ir.DataTypeComponent, 
                               comp_name: str, ctxt: ir.Context) -> List[str]:
        """Generate channel binding code for port-to-channel interface connections.
        
        Handles bindings like: self.subcomp.port : self.ch.put (or .get)
        """
        lines = []
        
        # Get the LHS port path (e.g., self->p.p or self->c.c)
        lhs_code = self._expr_to_c(lhs, comp, "self", ctxt)
        
        # Get the channel path (e.g., self->ch)
        channel_code = self._expr_to_c(rhs.base, comp, "self", ctxt)
        
        # Determine if this is put or get
        interface_type = rhs.ref  # "put" or "get"
        
        # Generate the binding: port points to the channel's interface
        # e.g., self->p.p = (zsp_put_if_t *)&self->ch;
        if interface_type == "put":
            lines.append(f"{lhs_code} = (zsp_put_if_t *)&{channel_code};")
        else:  # get
            lines.append(f"{lhs_code} = (zsp_get_if_t *)&{channel_code};")
        
        return lines

    def _generate_method_bind(self, lhs: ir.ExprRefPy, rhs, comp: ir.DataTypeComponent, 
                              comp_name: str, ctxt: ir.Context) -> List[str]:
        """Generate method binding code."""
        # lhs: ExprRefPy(base=ExprRefField(...export...), ref="method_name")
        # rhs: ExprRefPy(base=TypeExprRefSelf, ref="method_name") or similar
        
        method_name = lhs.ref
        export_code = self._expr_to_c(lhs.base, comp, "self", ctxt)
        
        # Get the target method name
        if isinstance(rhs, ir.ExprRefPy) and isinstance(rhs.base, ir.TypeExprRefSelf):
            # Binding to self.method -> use ComponentType_method
            target_method = f"{comp_name}_{rhs.ref}"
        else:
            target_method = self._expr_to_c(rhs, comp, "self", ctxt)
        
        lines = []
        # Set the method function pointer
        lines.append(f"{export_code}.{method_name} = (void *){target_method};")
        # Also set the self pointer if not already done
        lines.append(f"{export_code}.self = self;")
        
        return lines

    def _expr_to_c(self, expr, comp: ir.DataTypeComponent, self_name: str, ctxt: ir.Context) -> str:
        """Convert a datamodel expression to C code.
        
        Args:
            expr: The expression to convert
            comp: The component context for field name lookup
            self_name: The name to use for self references
            ctxt: The datamodel context for type lookups
        """
        if isinstance(expr, ir.ExprRefField):
            # Build field path recursively
            base = expr.base
            field_idx = expr.index
            
            if isinstance(base, ir.TypeExprRefSelf):
                # Direct field access on self: self->field_name
                if field_idx < len(comp.fields):
                    field_name = comp.fields[field_idx].name
                    return f"{self_name}->{field_name}"
                return f"{self_name}->field_{field_idx}"
            elif isinstance(base, ir.ExprRefField):
                # Nested field access: self->subcomp.field
                base_code = self._expr_to_c(base, comp, self_name, ctxt)
                
                # Get the type of the base to look up field names
                base_type = self._get_expr_type(base, comp, ctxt)
                if base_type and isinstance(base_type, ir.DataTypeComponent):
                    if field_idx < len(base_type.fields):
                        field_name = base_type.fields[field_idx].name
                        return f"{base_code}.{field_name}"
                return f"{base_code}.field_{field_idx}"
            
            return ""
            
        elif isinstance(expr, ir.TypeExprRefSelf):
            return self_name
            
        elif isinstance(expr, ir.ExprRefPy):
            base = self._expr_to_c(expr.base, comp, self_name, ctxt)
            return f"{base}.{expr.ref}" if base else expr.ref
            
        elif isinstance(expr, ir.ExprAttribute):
            value = self._expr_to_c(expr.value, comp, self_name, ctxt)
            if value == self_name:
                return f"{self_name}->{expr.attr}"
            else:
                return f"{value}.{expr.attr}"
                
        elif isinstance(expr, ir.ExprConstant):
            if expr.value == "self":
                return self_name
            return str(expr.value)
        
        return ""

    def _get_expr_type(self, expr, comp: ir.DataTypeComponent, ctxt: ir.Context) -> Optional[ir.DataType]:
        """Get the data type of an expression for field lookup."""
        if isinstance(expr, ir.ExprRefField):
            base = expr.base
            field_idx = expr.index
            
            if isinstance(base, ir.TypeExprRefSelf):
                # Get field type from component
                if field_idx < len(comp.fields):
                    field = comp.fields[field_idx]
                    dtype = field.datatype
                    # Resolve references
                    if isinstance(dtype, ir.DataTypeRef):
                        return ctxt.type_m.get(dtype.ref_name)
                    return dtype
            elif isinstance(base, ir.ExprRefField):
                # Get type of nested field
                base_type = self._get_expr_type(base, comp, ctxt)
                if base_type and isinstance(base_type, ir.DataTypeComponent):
                    if field_idx < len(base_type.fields):
                        field = base_type.fields[field_idx]
                        dtype = field.datatype
                        if isinstance(dtype, ir.DataTypeRef):
                            return ctxt.type_m.get(dtype.ref_name)
                        return dtype
        
        return None

    def _generate_method_params(self, func: ir.Function, comp_name: str) -> str:
        """Generate method parameter list for C function."""
        params = [f"{comp_name} *self"]
        
        if func.args and func.args.args:
            for arg in func.args.args:
                c_type = self._get_c_type_for_arg(arg)
                params.append(f"{c_type} {arg.arg}")
        
        return ", ".join(params)

    def _get_c_type_for_arg(self, arg) -> str:
        """Get C type for a function argument."""
        if arg.annotation and hasattr(arg.annotation, 'value'):
            ann_val = arg.annotation.value
            if hasattr(ann_val, '__name__'):
                type_name = ann_val.__name__
                if 'uint32' in type_name:
                    return "uint32_t"
                elif 'int32' in type_name:
                    return "int32_t"
                elif 'uint64' in type_name:
                    return "uint64_t"
                elif 'int64' in type_name:
                    return "int64_t"
                elif 'uint16' in type_name:
                    return "uint16_t"
                elif 'int16' in type_name:
                    return "int16_t"
                elif 'uint8' in type_name:
                    return "uint8_t"
                elif 'int8' in type_name:
                    return "int8_t"
        return "int32_t"  # Default
    
    def _get_func_return_type(self, func: ir.Function) -> str:
        """Get C return type for a function."""
        if not func.returns:
            return "void"
        
        ret_type = func.returns
        if isinstance(ret_type, ir.DataTypeInt):
            if ret_type.signed:
                if ret_type.bits <= 8:
                    return "int8_t"
                elif ret_type.bits <= 16:
                    return "int16_t"
                elif ret_type.bits <= 32:
                    return "int32_t"
                else:
                    return "int64_t"
            else:
                if ret_type.bits <= 8:
                    return "uint8_t"
                elif ret_type.bits <= 16:
                    return "uint16_t"
                elif ret_type.bits <= 32:
                    return "uint32_t"
                else:
                    return "uint64_t"
        
        return "int32_t"  # Default

    def _generate_method(self, comp: ir.DataTypeComponent, func: ir.Function, name: str, ctxt: ir.Context) -> List[str]:
        """Generate a component method."""
        
        # Check if this is an async method
        if getattr(func, 'is_async', False):
            return self._generate_async_method(comp, func, name, ctxt)
        
        # Get return type
        ret_type = self._get_method_return_type(func)
        
        params = self._generate_method_params(func, name)
        lines = [
            f"{ret_type} {name}_{func.name}({params}) {{",
        ]
        
        # Extract local variables from function body
        if func.body:
            local_vars = self._extract_method_local_vars(func.body, func.args)
            for var_name, var_type in local_vars:
                lines.append(f"    {var_type} {var_name};")
            if local_vars:
                lines.append("")
        
        # Get the method body from datamodel
        body_code = self._get_method_body(comp, func, ctxt)
        if body_code:
            # Indent the body
            for line in body_code.split("\n"):
                if line.strip():
                    lines.append(f"    {line}")
        
        lines.append("}")
        return lines

    def _generate_async_method(self, comp: ir.DataTypeComponent, func: ir.Function, name: str, ctxt: ir.Context) -> List[str]:
        """Generate a component async method as a C coroutine.
        
        If the analyzer determines this can be sync, generates both sync and async variants.
        
        Raises:
            RuntimeError: If async method body is not available in datamodel and cannot be retrieved from source.
        """
        lines = []
        
        # Check if this function can be converted to sync
        can_be_sync = False
        if self.async_analyzer:
            can_be_sync = self.async_analyzer.is_sync_convertible(comp.name, func.name)
        
        # Use the datamodel body - it must be populated by the DataModelFactory
        if not func.body:
            raise RuntimeError(
                f"Cannot generate async method '{func.name}' for component '{comp.name}': "
                f"method body is not available in datamodel. "
                f"Ensure DataModelFactory.build() is called with proper component classes "
                f"and that the source code is accessible."
            )
        
        # Generate sync variant if applicable
        if can_be_sync:
            sync_gen = SyncMethodGenerator(name, func.name, component=comp, ctxt=ctxt)
            sync_code = sync_gen.generate(func)
            lines.extend(sync_code.split("\n"))
            lines.append("")
        
        # Always generate async variant for backward compatibility
        dm_gen = DmAsyncMethodGenerator(name, func.name, component=comp, ctxt=ctxt)
        code = dm_gen.generate(func)
        lines.extend(code.split("\n"))
        return lines

    def _get_method_body(self, comp: ir.DataTypeComponent, func: ir.Function, ctxt: ir.Context) -> str:
        """Generate method body from datamodel."""
        # Use the datamodel body - it must be populated by the DataModelFactory
        if not func.body:
            return ""
        
        # Create a stmt generator with component context for field resolution
        stmt_gen = StmtGenerator(component=comp, ctxt=ctxt)
        stmt_gen.indent_level = 0
        lines = []
        for stmt in func.body:
            code = stmt_gen._gen_dm_stmt(stmt)
            if code:
                lines.append(code)
        return "\n".join(lines)
    
    def _get_method_return_type(self, func: ir.Function) -> str:
        """Get C return type for a method."""
        if not func.returns:
            return "void"
        
        return self.type_mapper.map_type(func.returns)
    
    def _extract_method_local_vars(self, stmts: List[ir.Stmt], args: ir.Arguments) -> List:
        """Extract local variable declarations from function body."""
        local_vars = []
        seen_vars = set()
        
        # Add function parameters to seen_vars
        if args and args.args:
            for arg in args.args:
                if arg.arg != 'self':
                    seen_vars.add(arg.arg)
        
        # Walk statements to find assignments
        def extract_from_stmt(stmt):
            if isinstance(stmt, ir.StmtAssign):
                for target in stmt.targets:
                    if isinstance(target, ir.ExprRefLocal):
                        var_name = target.name
                        if var_name not in seen_vars:
                            # Try to infer type from annotation or default to int32_t
                            var_type = "int32_t"
                            if hasattr(target, 'type') and target.type:
                                var_type = self.type_mapper.map_type(target.type)
                            local_vars.append((var_name, var_type))
                            seen_vars.add(var_name)
            elif isinstance(stmt, ir.StmtFor):
                # Mark for loop variable as seen (it's declared in the for statement)
                if hasattr(stmt, 'target') and isinstance(stmt.target, ir.ExprRefLocal):
                    seen_vars.add(stmt.target.name)
                # Handle variables in for loop body
                if hasattr(stmt, 'body'):
                    for s in stmt.body:
                        extract_from_stmt(s)
            elif isinstance(stmt, ir.StmtIf):
                if hasattr(stmt, 'body'):
                    for s in stmt.body:
                        extract_from_stmt(s)
                if hasattr(stmt, 'orelse'):
                    for s in stmt.orelse:
                        extract_from_stmt(s)
            elif isinstance(stmt, ir.StmtWhile):
                if hasattr(stmt, 'body'):
                    for s in stmt.body:
                        extract_from_stmt(s)
        
        for stmt in stmts:
            extract_from_stmt(stmt)
        
        return local_vars

    def _should_generate_method(self, func) -> bool:
        """Check if a method should be generated."""
        # Skip Process types - they're background processes, not callable methods
        if isinstance(func, ir.Process):
            return False
        # Skip internal/inherited methods
        if func.name.startswith("__"):
            return False
        if func.name in ("shutdown", "time", "wait", "__bind__"):
            return False
        return True

    def _generate_comb_process(self, comp: ir.DataTypeComponent, func: ir.Function, name: str, ctxt: ir.Context) -> List[str]:
        """Generate a combinational process as a C function.
        
        Comb processes are simple C functions that immediately update outputs based on inputs.
        They don't use coroutines or async machinery.
        """
        lines = [
            f"/* Combinational process: {func.name} */",
        ]
        
        # Add sensitivity list as a comment
        sensitivity = func.metadata.get('sensitivity', [])
        if sensitivity:
            sens_names = []
            for sens_expr in sensitivity:
                if isinstance(sens_expr, ir.ExprRefField) and hasattr(sens_expr, 'index'):
                    if sens_expr.index < len(comp.fields):
                        sens_names.append(comp.fields[sens_expr.index].name)
            if sens_names:
                lines.append(f"/* Sensitive to: {', '.join(sens_names)} */")
        
        # Function signature
        lines.append(f"void {name}_{func.name}({name} *self) {{")
        
        # Generate function body using statement generator
        if func.body:
            stmt_gen = StmtGenerator(comp, ctxt)
            stmt_gen.indent_level = 1
            for stmt in func.body:
                body_line = stmt_gen._gen_dm_stmt(stmt)
                if body_line:  # Skip empty lines from docstrings
                    lines.append(body_line)
        
        lines.append("}")
        
        return lines
    
    def _generate_sync_process(self, comp: ir.DataTypeComponent, func: ir.Function, name: str, ctxt: ir.Context) -> List[str]:
        """Generate a synchronous process as a C function.
        
        Sync processes are triggered on clock edges and update state accordingly.
        For now, we generate them as simple functions similar to comb processes.
        """
        lines = [
            f"/* Synchronous process: {func.name} */",
        ]
        
        # Add clock/reset info from metadata if available
        if 'clock' in func.metadata:
            lines.append(f"/* Triggered on clock edge */")
        if 'reset' in func.metadata:
            lines.append(f"/* Uses reset signal */")
        
        # Function signature
        lines.append(f"void {name}_{func.name}({name} *self) {{")
        
        # Generate function body using statement generator
        if func.body:
            stmt_gen = StmtGenerator(comp, ctxt)
            stmt_gen.indent_level = 1
            for stmt in func.body:
                body_line = stmt_gen._gen_dm_stmt(stmt)
                if body_line:  # Skip empty lines from docstrings
                    lines.append(body_line)
        
        lines.append("}")
        
        return lines

    def _generate_process_task(self, comp: ir.DataTypeComponent, func: ir.Process, name: str, ctxt: ir.Context) -> List[str]:
        """Generate a task wrapper for a Process function.
        
        The process body is generated using async-to-sync conversion.
        This wrapper creates the zsp_thread task function signature.
        """
        lines = [
            f"/* Process task: {func.name} */",
            f"zsp_frame_t* {name}_{func.name}_task(",
            f"    zsp_timebase_t *timebase,",
            f"    zsp_thread_t *thread,",
            f"    int idx,",
            f"    va_list *args) {{",
            f"    /* Get component instance from args */",
            f"    {name} *self = ({name}*)zsp_timebase_va_arg(args, sizeof({name}*));",
            f"    ",
            f"    /* Call the process implementation */",
            f"    /* NOTE: The actual process body with wait() calls should be */",
            f"    /* generated by the async-to-sync converter. For now, this is */",
            f"    /* a placeholder that immediately returns. */",
            f"    ",
            f"    /* Placeholder: Just yield once and exit */",
            f"    if (idx == 0) {{",
            f"        zsp_timebase_yield(thread);",
            f"        return thread->leaf;",
            f"    }}",
            f"    ",
            f"    /* Process complete */",
            f"    return NULL;",
            f"}}",
        ]
        
        return lines
    
    def _generate_process_startup(self, comp: ir.DataTypeComponent, processes: List[ir.Process], name: str, ctxt: ir.Context) -> List[str]:
        """Generate the start_processes function for the component.
        
        This creates threads for all @process functions and schedules them.
        Uses the timebase stored in the component instance.
        """
        lines = [
            f"/* Start all processes for {name} */",
            f"void {name}_start_processes({name} *self) {{",
            f"    /* Use the timebase stored in the component */",
            f"    if (!self->timebase) {{",
            f"        /* No timebase available - processes cannot run */",
            f"        return;",
            f"    }}",
            f"    ",
        ]
        
        # Create a thread for each process
        for proc in processes:
            lines.extend([
                f"    /* Start process: {proc.name} */",
                f"    zsp_timebase_thread_create(",
                f"        self->timebase,",
                f"        {name}_{proc.name}_task,",
                f"        ZSP_THREAD_FLAGS_INITIAL,",
                f"        self);",
                f"    ",
            ])
        
        lines.append("}")
        
        return lines
    
    def _generate_main(self, ctxt: ir.Context):
        """Generate main test harness."""
        lines = [
            "#include <stdio.h>",
            "#include <stdlib.h>",
            '#include "zsp_alloc.h"',
            '#include "zsp_init_ctxt.h"',
        ]
        
        # Include headers for all components
        for orig_name, dtype in ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeComponent):
                name = sanitize_c_name(orig_name)
                lines.append(f'#include "{name.lower()}.h"')
        
        lines.extend([
            "",
            "int main(int argc, char **argv) {",
            "    zsp_alloc_t alloc;",
            "    zsp_alloc_malloc_init(&alloc);",
            "",
            "    zsp_init_ctxt_t ctxt;",
            "    ctxt.alloc = &alloc;",
            "",
        ])
        
        # Instantiate and call hello on each component
        for orig_name, dtype in ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeComponent):
                name = sanitize_c_name(orig_name)
                var_name = name.lower()
                lines.extend([
                    f"    {name} {var_name};",
                    f'    {name}_init(&ctxt, &{var_name}, "{var_name}", NULL);',
                ])
                
                # Call hello if it exists
                for func in dtype.functions:
                    if func.name == "hello":
                        lines.append(f"    {name}_hello(&{var_name});")
                        break
        
        lines.extend([
            "",
            "    return 0;",
            "}",
        ])
        
        self.output.add_source("main", "\n".join(lines))

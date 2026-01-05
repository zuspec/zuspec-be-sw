"""
Library Wrapper Generator

Generates C library wrapper functions for Python ctypes binding.
Creates create/destroy and accessor functions for existing C components.
"""

from pathlib import Path
from typing import List
from zuspec.dataclasses import ir


class LibraryWrapperGenerator:
    """Generates C wrapper functions for library export."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
    
    def generate_wrapper(self, comp: ir.DataTypeComponent, comp_name: str) -> tuple[str, str]:
        """Generate wrapper header and implementation for a component.
        
        Args:
            comp: Component datamodel
            comp_name: Sanitized component name
            
        Returns:
            Tuple of (header_content, impl_content)
        """
        header_lines = []
        impl_lines = []
        
        # Header guard
        guard = f"INCLUDED_{comp_name.upper()}_API_H"
        header_lines.extend([
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
            f"#include \"{comp_name.lower()}.h\"",
            "",
            "#ifdef __cplusplus",
            "extern \"C\" {",
            "#endif",
            "",
            "/* Library API functions */",
            ""
        ])
        
        # Implementation includes
        impl_lines.extend([
            f"#include \"{comp_name}_api.h\"",
            "#include <stdlib.h>",
            "#include <string.h>",
            "#include \"zsp_rt.h\"",
            "#include \"zsp_alloc.h\"",
            "#include \"zsp_timebase.h\"",
            "",
            "/* Global timebase and allocator for this component library */",
            f"zsp_timebase_t *g_{comp_name}_timebase = NULL;",
            f"zsp_alloc_t *g_{comp_name}_alloc = NULL;",
            "",
        ])
        
        # Create function
        header_lines.extend([
            f"/* Create a new {comp_name} instance */",
            f"{comp_name}* {comp_name}_create(void);",
            ""
        ])
        
        impl_lines.extend([
            f"{comp_name}* {comp_name}_create(void) {{",
            f"    {comp_name} *inst = ({comp_name}*)malloc(sizeof({comp_name}));",
            f"    if (inst) {{",
            f"        /* Create global allocator if needed */",
            f"        if (!g_{comp_name}_alloc) {{",
            f"            g_{comp_name}_alloc = zsp_alloc_malloc_create();",
            f"        }}",
            f"        ",
            f"        /* Create global timebase if needed */",
            f"        if (!g_{comp_name}_timebase) {{",
            f"            g_{comp_name}_timebase = zsp_timebase_create(",
            f"                g_{comp_name}_alloc,",
            f"                ZSP_TIME_NS);  /* Nanosecond resolution */",
            f"        }}",
            f"        ",
            f"        /* Create initialization context */",
            f"        zsp_init_ctxt_t ctxt;",
            f"        ctxt.alloc = g_{comp_name}_alloc;",
            f"        ctxt.api = NULL;",
            f"        ctxt.timebase = g_{comp_name}_timebase;",
            f"        ",
            f"        /* Initialize component */",
            f"        memset(inst, 0, sizeof({comp_name}));",
            f"        {comp_name}_init(&ctxt, inst, \"{comp_name}\", NULL);",
            f"    }}",
            f"    return inst;",
            f"}}",
            ""
        ])
        
        # Destroy function
        header_lines.extend([
            f"/* Destroy a {comp_name} instance */",
            f"void {comp_name}_destroy({comp_name}* inst);",
            ""
        ])
        
        impl_lines.extend([
            f"void {comp_name}_destroy({comp_name}* inst) {{",
            f"    if (inst) {{",
            f"        /* TODO: Cleanup any resources */",
            f"        free(inst);",
            f"    }}",
            f"}}",
            "",
        ])
        
        # Timebase control functions
        header_lines.extend([
            "/* Timebase control functions - operate on component's timebase */",
            f"int {comp_name}_timebase_run({comp_name}* inst);",
            f"int {comp_name}_timebase_advance({comp_name}* inst);",
            f"int {comp_name}_timebase_has_pending({comp_name}* inst);",
            f"uint64_t {comp_name}_timebase_current_time({comp_name}* inst);",
            f"void {comp_name}_start_processes({comp_name}* inst);",
            ""
        ])
        
        impl_lines.extend([
            f"int {comp_name}_timebase_run({comp_name}* inst) {{",
            f"    if (!inst || !inst->timebase) return 0;",
            f"    return zsp_timebase_run(inst->timebase);",
            f"}}",
            "",
            f"int {comp_name}_timebase_advance({comp_name}* inst) {{",
            f"    if (!inst || !inst->timebase) return 0;",
            f"    return zsp_timebase_advance(inst->timebase);",
            f"}}",
            "",
            f"int {comp_name}_timebase_has_pending({comp_name}* inst) {{",
            f"    if (!inst || !inst->timebase) return 0;",
            f"    return zsp_timebase_has_pending(inst->timebase);",
            f"}}",
            "",
            f"uint64_t {comp_name}_timebase_current_time({comp_name}* inst) {{",
            f"    if (!inst || !inst->timebase) return 0;",
            f"    return zsp_timebase_current_ticks(inst->timebase);",
            f"}}",
            "",
            f"__attribute__((weak)) void {comp_name}_start_processes({comp_name}* inst) {{",
            f"    /* Start all @process functions for this component */",
            f"    /* C generator will provide strong symbol if processes exist */",
            f"    (void)inst;  /* Unused for components without processes */",
            f"}}",
            ""
        ])
        
        # Generate accessors for input/output signals
        # The C generator will create methods if they're explicitly defined in Python
        # We generate simple accessors only for signals without explicit methods
        # Using weak linkage so explicit methods can override
        for field in comp.fields:
            # Check if it's an InOut field (has is_out attribute)
            if isinstance(field, ir.FieldInOut):
                # Get C type for the field
                c_type = self._get_field_c_type(field.datatype)
                
                # Getter
                header_lines.extend([
                    f"/* Get {field.name} value */",
                    f"{c_type} {comp_name}_get_{field.name}({comp_name}* inst);",
                    ""
                ])
                
                # Use weak attribute so explicit methods can override
                impl_lines.extend([
                    f"__attribute__((weak)) {c_type} {comp_name}_get_{field.name}({comp_name}* inst) {{",
                    f"    return inst->{field.name};",
                    f"}}",
                    ""
                ])
                
                # Setter
                header_lines.extend([
                    f"/* Set {field.name} value */",
                    f"void {comp_name}_set_{field.name}({comp_name}* inst, {c_type} value);",
                    ""
                ])
                
                impl_lines.extend([
                    f"__attribute__((weak)) void {comp_name}_set_{field.name}({comp_name}* inst, {c_type} value) {{",
                    f"    inst->{field.name} = value;",
                    f"}}",
                    ""
                ])
        
        # Close header
        header_lines.extend([
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            f"#endif /* {guard} */",
            ""
        ])
        
        return "\n".join(header_lines), "\n".join(impl_lines)
    
    def _get_field_c_type(self, datatype: ir.DataType) -> str:
        """Get C type for a field datatype.
        
        Args:
            datatype: Field datatype
            
        Returns:
            C type string
        """
        if isinstance(datatype, ir.DataTypeInt):
            # Use bits field for width, default to 32 if not specified
            width = datatype.bits if datatype.bits > 0 else 32
            if datatype.signed:
                if width <= 8:
                    return "int8_t"
                elif width <= 16:
                    return "int16_t"
                elif width <= 32:
                    return "int32_t"
                else:
                    return "int64_t"
            else:
                if width <= 8:
                    return "uint8_t"
                elif width <= 16:
                    return "uint16_t"
                elif width <= 32:
                    return "uint32_t"
                else:
                    return "uint64_t"
        
        # Default to uint32_t for unknown types
        return "uint32_t"
    
    def write_wrapper(self, comp: ir.DataTypeComponent, comp_name: str) -> List[Path]:
        """Write wrapper files to disk.
        
        Args:
            comp: Component datamodel
            comp_name: Sanitized component name
            
        Returns:
            List of generated file paths
        """
        header_content, impl_content = self.generate_wrapper(comp, comp_name)
        
        header_path = self.output_dir / f"{comp_name}_api.h"
        impl_path = self.output_dir / f"{comp_name}_api.c"
        
        header_path.write_text(header_content)
        impl_path.write_text(impl_content)
        
        return [header_path, impl_path]

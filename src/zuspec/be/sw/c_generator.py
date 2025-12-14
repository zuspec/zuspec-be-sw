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
import ast
import inspect
import re
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Type

from zuspec.dataclasses import dm

from .type_mapper import TypeMapper
from .expr_generator import ExprGenerator
from .stmt_generator import StmtGenerator
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

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.type_mapper = TypeMapper()
        self.expr_gen = ExprGenerator()
        self.stmt_gen = StmtGenerator()
        self.output = OutputManager(output_dir)

    def generate(self, ctxt: dm.Context) -> List[Path]:
        """Generate C code for all types in context."""
        for name, dtype in ctxt.type_m.items():
            if isinstance(dtype, dm.DataTypeComponent):
                self._generate_component(dtype)
        
        # Generate test harness
        self._generate_main(ctxt)
        
        return self.output.write_all()

    def _generate_component(self, comp: dm.DataTypeComponent):
        """Generate C code for a component."""
        name = sanitize_c_name(comp.name)
        
        # Generate header
        header = self._generate_component_header(comp, name)
        self.output.add_header(name.lower(), header)
        
        # Generate implementation
        impl = self._generate_component_impl(comp, name)
        self.output.add_source(name.lower(), impl)


    def _generate_component_header(self, comp: dm.DataTypeComponent, name: str) -> str:
        """Generate component header file."""
        guard = f"INCLUDED_{name.upper()}_H"
        
        lines = [
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
            "#include <stdio.h>",
            "#include <stdint.h>",
            '#include "zsp_component.h"',
            '#include "zsp_init_ctxt.h"',
            "",
            f"/* Forward declaration */",
            f"struct {name};",
            "",
            f"/* {name} type definition */",
            f"typedef struct {name} {{",
            f"    zsp_component_t base;",
        ]
        
        # Add fields
        for field in comp.fields:
            c_type = self.type_mapper.map_type(field.dtype)
            lines.append(f"    {c_type} {field.name};")
        
        lines.append(f"}} {name};")
        lines.append("")
        
        # Function declarations
        lines.append(f"/* Initialize {name} */")
        lines.append(f"void {name}_init(")
        lines.append(f"    zsp_init_ctxt_t *ctxt,")
        lines.append(f"    {name} *self,")
        lines.append(f"    const char *name,")
        lines.append(f"    zsp_component_t *parent);")
        lines.append("")
        
        # Method declarations
        for func in comp.functions:
            if self._should_generate_method(func):
                lines.append(f"void {name}_{func.name}({name} *self);")
        
        lines.append("")
        lines.append(f"#endif /* {guard} */")
        
        return "\n".join(lines)

    def _generate_component_impl(self, comp: dm.DataTypeComponent, name: str) -> str:
        """Generate component implementation file."""
        
        lines = [
            f'#include "{name.lower()}.h"',
            '#include "zsp_init_ctxt.h"',
            "",
        ]
        
        # Generate init function
        lines.extend(self._generate_init_function(comp, name))
        lines.append("")
        
        # Generate methods
        for func in comp.functions:
            if self._should_generate_method(func):
                method_code = self._generate_method(comp, func, name)
                lines.extend(method_code)
                lines.append("")
        
        return "\n".join(lines)

    def _generate_init_function(self, comp: dm.DataTypeComponent, name: str) -> List[str]:
        """Generate component initialization function."""
        
        lines = [
            f"void {name}_init(",
            f"    zsp_init_ctxt_t *ctxt,",
            f"    {name} *self,",
            f"    const char *name,",
            f"    zsp_component_t *parent) {{",
            f"    zsp_component_init(ctxt, &self->base, name, parent);",
        ]
        
        # Initialize fields
        for field in comp.fields:
            default = self.type_mapper.get_default_value(field.dtype)
            if default:
                lines.append(f"    self->{field.name} = {default};")
        
        lines.append("}")
        return lines

    def _generate_method(self, comp: dm.DataTypeComponent, func: dm.Function, name: str) -> List[str]:
        """Generate a component method."""
        
        lines = [
            f"void {name}_{func.name}({name} *self) {{",
        ]
        
        # Get the method body from Python source
        body_code = self._get_method_body(comp, func)
        if body_code:
            # Indent the body
            for line in body_code.split("\n"):
                if line.strip():
                    lines.append(f"    {line}")
        
        lines.append("}")
        return lines

    def _get_method_body(self, comp: dm.DataTypeComponent, func: dm.Function) -> str:
        """Extract and convert method body from Python source."""
        py_type = comp.py_type
        if py_type is None:
            return ""
        
        # Try to get the method
        method = getattr(py_type, func.name, None)
        if method is None:
            return ""
        
        try:
            # Get source code
            source = inspect.getsource(method)
            # Parse to AST
            tree = ast.parse(textwrap.dedent(source))
            
            if tree.body and isinstance(tree.body[0], ast.FunctionDef):
                func_def = tree.body[0]
                # Generate C code for the body
                self.stmt_gen.indent_level = 0
                return self.stmt_gen.generate(func_def.body)
        except (OSError, TypeError):
            # Source not available (e.g., built-in or dynamically defined)
            pass
        
        return ""

    def _should_generate_method(self, func: dm.Function) -> bool:
        """Check if a method should be generated."""
        # Skip internal/inherited methods
        if func.name.startswith("__"):
            return False
        if func.name in ("shutdown", "time", "wait", "__bind__"):
            return False
        return True

    def _generate_main(self, ctxt: dm.Context):
        """Generate main test harness."""
        lines = [
            "#include <stdio.h>",
            "#include <stdlib.h>",
            '#include "zsp_alloc.h"',
            '#include "zsp_init_ctxt.h"',
        ]
        
        # Include headers for all components
        for orig_name, dtype in ctxt.type_m.items():
            if isinstance(dtype, dm.DataTypeComponent):
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
            if isinstance(dtype, dm.DataTypeComponent):
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

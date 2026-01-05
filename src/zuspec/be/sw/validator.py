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
from typing import List, Optional
from zuspec.dataclasses import ir


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

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []

    def validate(self, ctxt: ir.Context) -> bool:
        """Validate all types in the context."""
        for name, dtype in ctxt.type_m.items():
            self._validate_type(dtype)
        return self.is_valid()

    def validate_component(self, comp: ir.DataTypeComponent) -> bool:
        """Validate a single component."""
        self._validate_type(comp)
        return self.is_valid()

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0

    def _validate_type(self, dtype: ir.DataType):
        """Validate a datamodel type."""
        if isinstance(dtype, ir.DataTypeComponent):
            self._validate_component(dtype)
        elif isinstance(dtype, ir.DataTypeStruct):
            self._validate_struct(dtype)
        elif isinstance(dtype, ir.DataTypeProtocol):
            self._validate_protocol(dtype)

    def _validate_component(self, comp: ir.DataTypeComponent):
        """Validate a component type."""
        for field in comp.fields:
            self._validate_field(field)
        
        for func in comp.functions:
            self._validate_function(func, comp.name)

    def _validate_struct(self, struct: ir.DataTypeStruct):
        """Validate a struct type."""
        for field in struct.fields:
            self._validate_field(field)

    def _validate_protocol(self, proto: ir.DataTypeProtocol):
        """Validate a protocol type."""
        # Protocols map to vtables in C
        pass

    def _validate_field(self, field: ir.Field):
        """Validate a field."""
        # Fields need type annotations for C
        if field.dtype is None:
            self.errors.append(ValidationError(
                f"Field '{field.name}' missing type annotation"
            ))

    def _validate_function(self, func: ir.Function, type_name: str):
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

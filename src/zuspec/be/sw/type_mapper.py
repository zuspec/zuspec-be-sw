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
Type mapping utilities for converting datamodel types to C types.
"""
import re
from typing import Optional
from zuspec.dataclasses import dm


def sanitize_protocol_name(name: str) -> str:
    """Sanitize a protocol name to be a valid C identifier."""
    if '.' in name:
        name = name.split('.')[-1]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if name and name[0].isdigit():
        name = '_' + name
    return name


class TypeMapper:
    """Maps datamodel types to C type strings."""

    # Mapping of int bit widths to C types
    INT_TYPE_MAP = {
        (8, True): "int8_t",
        (8, False): "uint8_t",
        (16, True): "int16_t",
        (16, False): "uint16_t",
        (32, True): "int32_t",
        (32, False): "uint32_t",
        (64, True): "int64_t",
        (64, False): "uint64_t",
    }

    def map_type(self, dtype: dm.DataType, is_port: bool = False, is_export: bool = False, 
                 is_subcomponent: bool = False) -> str:
        """Map a datamodel type to its C representation.
        
        Args:
            dtype: The data type to map
            is_port: If True, this is a port field (pointer to API)
            is_export: If True, this is an export field (embedded API struct)
            is_subcomponent: If True, this is a sub-component (embedded struct)
        """
        if dtype is None:
            return "void"
        
        if isinstance(dtype, dm.DataTypeInt):
            return self._map_int_type(dtype)
        elif isinstance(dtype, dm.DataTypeString):
            return "const char*"
        elif isinstance(dtype, dm.DataTypeProtocol):
            # Protocol types: ports are pointers, exports are embedded
            name = sanitize_protocol_name(dtype.name)
            if is_port:
                return f"{name}_t *"
            else:  # export or general reference
                return f"{name}_t"
        elif isinstance(dtype, dm.DataTypeComponent):
            name = sanitize_protocol_name(dtype.name)
            if is_subcomponent:
                return name  # Embedded struct
            return f"{name} *"  # Pointer to component
        elif isinstance(dtype, dm.DataTypeStruct):
            return f"struct {dtype.name}*"
        elif isinstance(dtype, dm.DataTypeRef):
            # Reference to another type - check if it's a protocol reference
            name = dtype.ref_name
            if is_port:
                return f"{name}_t *"
            elif is_export:
                return f"{name}_t"
            elif is_subcomponent:
                return sanitize_protocol_name(name)  # Embedded struct
            else:
                return f"struct {dtype.ref_name}*"
        else:
            return "void*"

    def _map_int_type(self, dtype: dm.DataTypeInt) -> str:
        """Map an integer datamodel type to C type."""
        key = (dtype.bits, dtype.signed)
        if key in self.INT_TYPE_MAP:
            return self.INT_TYPE_MAP[key]
        # Default to closest larger type
        if dtype.signed:
            if dtype.bits <= 8:
                return "int8_t"
            elif dtype.bits <= 16:
                return "int16_t"
            elif dtype.bits <= 32:
                return "int32_t"
            else:
                return "int64_t"
        else:
            if dtype.bits <= 8:
                return "uint8_t"
            elif dtype.bits <= 16:
                return "uint16_t"
            elif dtype.bits <= 32:
                return "uint32_t"
            else:
                return "uint64_t"

    def get_default_value(self, dtype: dm.DataType) -> str:
        """Get default initializer value for a type."""
        if dtype is None:
            return ""
        if isinstance(dtype, dm.DataTypeInt):
            return "0"
        elif isinstance(dtype, dm.DataTypeString):
            return "NULL"
        else:
            return "NULL"

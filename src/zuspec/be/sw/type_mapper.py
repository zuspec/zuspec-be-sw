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
Supports type specialization for direct C code generation (Phase 1-3 of optimization plan).
"""
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from zuspec.dataclasses import ir


def sanitize_protocol_name(name: str) -> str:
    """Sanitize a protocol name to be a valid C identifier."""
    if '.' in name:
        name = name.split('.')[-1]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if name and name[0].isdigit():
        name = '_' + name
    return name


@dataclass
class TypeInfo:
    """Type information for specialized code generation."""
    c_type: str  # C type string (e.g., "uint32_t")
    element_type: Optional[str] = None  # For arrays/channels
    size: Optional[int] = None  # For fixed-size arrays
    capacity: Optional[int] = None  # For channels
    is_direct_array: bool = False  # True if direct C array (not wrapper)


class TypeMapper:
    """Maps datamodel types to C type strings with specialization support."""

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

    def __init__(self, enable_specialization: bool = False):
        """Initialize TypeMapper.
        
        Args:
            enable_specialization: If True, generate specialized direct C types instead of generic wrappers
        """
        self.enable_specialization = enable_specialization

    def map_type(self, dtype: ir.DataType, is_port: bool = False, is_export: bool = False, 
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
        
        if isinstance(dtype, ir.DataTypeInt):
            return self._map_int_type(dtype)
        elif isinstance(dtype, ir.DataTypeString):
            return "const char*"
        elif isinstance(dtype, ir.DataTypeMemory):
            # With specialization, we don't generate a type here - memory becomes direct array fields
            # The caller should use get_type_info() for detailed field generation
            if self.enable_specialization:
                return None  # Signal to generate specialized fields
            return "zsp_memory_t"
        elif isinstance(dtype, ir.DataTypeChannel):
            # With specialization, we don't generate a type here - channel becomes direct ring buffer
            # The caller should use get_type_info() for detailed field generation
            if self.enable_specialization:
                return None  # Signal to generate specialized fields
            return "zsp_channel_t"
        elif isinstance(dtype, ir.DataTypeGetIF):
            # GetIF - ports are pointers, exports embedded
            if is_port:
                return "zsp_get_if_t *"
            return "zsp_get_if_t"
        elif isinstance(dtype, ir.DataTypePutIF):
            # PutIF - ports are pointers, exports embedded
            if is_port:
                return "zsp_put_if_t *"
            return "zsp_put_if_t"
        elif isinstance(dtype, ir.DataTypeProtocol):
            # Protocol types: ports are pointers, exports are embedded
            name = sanitize_protocol_name(dtype.name)
            if is_port:
                return f"{name}_t *"
            else:  # export or general reference
                return f"{name}_t"
        elif isinstance(dtype, ir.DataTypeComponent):
            name = sanitize_protocol_name(dtype.name)
            if is_subcomponent:
                return name  # Embedded struct
            return f"{name} *"  # Pointer to component
        elif isinstance(dtype, ir.DataTypeStruct):
            return f"struct {dtype.name}*"
        elif isinstance(dtype, ir.DataTypeRef):
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

    def map_element_type(self, dtype: ir.DataType) -> str:
        """Map the element type for channels and interfaces.
        
        Returns C type string for the channel element type.
        For structs, returns pointer type. For primitives, returns value type.
        """
        if dtype is None:
            return "uintptr_t"
        
        if isinstance(dtype, ir.DataTypeInt):
            return self._map_int_type(dtype)
        elif isinstance(dtype, ir.DataTypeString):
            return "const char*"
        elif isinstance(dtype, (ir.DataTypeStruct, ir.DataTypeComponent, ir.DataTypeRef)):
            # Struct types are passed by pointer through channels
            if isinstance(dtype, ir.DataTypeRef):
                return f"{sanitize_protocol_name(dtype.ref_name)} *"
            return f"{sanitize_protocol_name(dtype.name)} *"
        else:
            return "uintptr_t"

    def get_element_size(self, dtype: ir.DataType) -> str:
        """Get the element size expression for channel initialization.
        
        Returns C expression for sizeof the element type.
        """
        if dtype is None:
            return "0"  # uintptr_t - use default
        
        if isinstance(dtype, ir.DataTypeInt):
            c_type = self._map_int_type(dtype)
            return f"sizeof({c_type})"
        elif isinstance(dtype, (ir.DataTypeStruct, ir.DataTypeComponent, ir.DataTypeRef)):
            # Structs passed by pointer
            return "sizeof(void *)"
        else:
            return "0"  # uintptr_t default

    def _map_int_type(self, dtype: ir.DataTypeInt) -> str:
        """Map an integer datamodel type to C type."""
        key = (dtype.bits, dtype.signed)
        if key in self.INT_TYPE_MAP:
            return self.INT_TYPE_MAP[key]
        
        # Handle unspecified bits (-1) as default int32_t
        bits = dtype.bits
        if bits < 0:
            bits = 32
        
        # Default to closest larger type
        if dtype.signed:
            if bits <= 8:
                return "int8_t"
            elif bits <= 16:
                return "int16_t"
            elif bits <= 32:
                return "int32_t"
            else:
                return "int64_t"
        else:
            if bits <= 8:
                return "uint8_t"
            elif bits <= 16:
                return "uint16_t"
            elif bits <= 32:
                return "uint32_t"
            else:
                return "uint64_t"

    def get_default_value(self, dtype: ir.DataType) -> str:
        """Get default initializer value for a type."""
        if dtype is None:
            return ""
        if isinstance(dtype, ir.DataTypeInt):
            return "0"
        elif isinstance(dtype, ir.DataTypeString):
            return "NULL"
        else:
            return "NULL"

    def get_type_info(self, dtype: ir.DataType) -> TypeInfo:
        """Get detailed type information for specialized code generation.
        
        This is used for Phase 1-2 of type specialization to generate
        direct C arrays and ring buffers instead of generic wrappers.
        
        Args:
            dtype: The data type to analyze
            
        Returns:
            TypeInfo with details for code generation
        """
        if isinstance(dtype, ir.DataTypeMemory):
            # Memory: Generate as direct C array
            elem_type = self.map_type(dtype.element_type) if hasattr(dtype, 'element_type') else "uint8_t"
            size = dtype.size if hasattr(dtype, 'size') else 65536
            return TypeInfo(
                c_type=elem_type,
                element_type=elem_type,
                size=size,
                is_direct_array=True
            )
        elif isinstance(dtype, ir.DataTypeChannel):
            # Channel: Generate as ring buffer with head/tail/count
            elem_type = self.map_element_type(dtype.element_type) if hasattr(dtype, 'element_type') else "uint32_t"
            capacity = dtype.capacity if hasattr(dtype, 'capacity') else 16
            return TypeInfo(
                c_type=elem_type,
                element_type=elem_type,
                capacity=capacity,
                is_direct_array=False
            )
        else:
            # Regular type - just return the C type
            c_type = self.map_type(dtype)
            return TypeInfo(c_type=c_type)

    def get_memory_element_type(self, mem_dtype: ir.DataTypeMemory) -> str:
        """Get the element type for a memory.
        
        Args:
            mem_dtype: Memory data type
            
        Returns:
            C type string for memory elements (e.g., "uint8_t")
        """
        if hasattr(mem_dtype, 'element_type') and mem_dtype.element_type:
            return self.map_type(mem_dtype.element_type)
        return "uint8_t"  # Default to byte array

    def get_memory_size(self, mem_dtype: ir.DataTypeMemory) -> int:
        """Get the size of a memory array.
        
        Args:
            mem_dtype: Memory data type
            
        Returns:
            Number of elements in the memory
        """
        if hasattr(mem_dtype, 'size'):
            return mem_dtype.size
        return 65536  # Default size

    def get_channel_capacity(self, ch_dtype: ir.DataTypeChannel) -> int:
        """Get the capacity of a channel.
        
        Args:
            ch_dtype: Channel data type
            
        Returns:
            Maximum number of elements the channel can hold
        """
        if hasattr(ch_dtype, 'capacity'):
            return ch_dtype.capacity
        return 16  # Default capacity

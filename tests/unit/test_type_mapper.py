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
Unit tests for the type_mapper module.
"""
import pytest
from zuspec.dataclasses import dm
from zuspec.be.sw.type_mapper import TypeMapper


class TestTypeMapper:
    """Tests for TypeMapper class."""

    def test_map_none_to_void(self):
        """Test that None maps to void."""
        mapper = TypeMapper()
        assert mapper.map_type(None) == "void"

    def test_map_int32_signed(self):
        """Test mapping signed 32-bit integer."""
        mapper = TypeMapper()
        dtype = dm.DataTypeInt(bits=32, signed=True)
        assert mapper.map_type(dtype) == "int32_t"

    def test_map_int32_unsigned(self):
        """Test mapping unsigned 32-bit integer."""
        mapper = TypeMapper()
        dtype = dm.DataTypeInt(bits=32, signed=False)
        assert mapper.map_type(dtype) == "uint32_t"

    def test_map_int8_signed(self):
        """Test mapping signed 8-bit integer."""
        mapper = TypeMapper()
        dtype = dm.DataTypeInt(bits=8, signed=True)
        assert mapper.map_type(dtype) == "int8_t"

    def test_map_int64_unsigned(self):
        """Test mapping unsigned 64-bit integer."""
        mapper = TypeMapper()
        dtype = dm.DataTypeInt(bits=64, signed=False)
        assert mapper.map_type(dtype) == "uint64_t"

    def test_map_string(self):
        """Test mapping string type."""
        mapper = TypeMapper()
        dtype = dm.DataTypeString()
        assert mapper.map_type(dtype) == "const char*"

    def test_map_non_standard_int_bits(self):
        """Test mapping integers with non-standard bit widths."""
        mapper = TypeMapper()
        # 12 bits should round up to 16
        dtype = dm.DataTypeInt(bits=12, signed=True)
        assert mapper.map_type(dtype) == "int16_t"
        
        # 5 bits should round up to 8
        dtype = dm.DataTypeInt(bits=5, signed=False)
        assert mapper.map_type(dtype) == "uint8_t"

    def test_get_default_value_int(self):
        """Test getting default value for integer type."""
        mapper = TypeMapper()
        dtype = dm.DataTypeInt(bits=32, signed=True)
        assert mapper.get_default_value(dtype) == "0"

    def test_get_default_value_string(self):
        """Test getting default value for string type."""
        mapper = TypeMapper()
        dtype = dm.DataTypeString()
        assert mapper.get_default_value(dtype) == "NULL"

    def test_get_default_value_none(self):
        """Test getting default value for None type."""
        mapper = TypeMapper()
        assert mapper.get_default_value(None) == ""

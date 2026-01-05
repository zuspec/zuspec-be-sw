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
Unit tests for the validator module.
"""
import pytest
from zuspec.dataclasses import ir
from zuspec.be.sw.validator import CValidator, ValidationError


class TestCValidator:
    """Tests for CValidator class - datamodel validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CValidator()

    def test_is_valid_initially(self):
        """Test that validator starts valid."""
        assert self.validator.is_valid()
        assert len(self.validator.errors) == 0

    def test_error_str_with_location(self):
        """Test ValidationError string representation with location."""
        error = ValidationError("Test error", "test.py:10")
        assert "test.py:10" in str(error)
        assert "Test error" in str(error)

    def test_error_str_without_location(self):
        """Test ValidationError string representation without location."""
        error = ValidationError("Test error")
        assert str(error) == "Test error"

    def test_validate_empty_context(self):
        """Test validating empty context."""
        ctxt = ir.Context(type_m={})
        result = self.validator.validate(ctxt)
        assert result is True

    def test_validate_component_with_no_fields(self):
        """Test validating component with no fields."""
        comp = ir.DataTypeComponent(
            name="TestComp",
            py_type=None,
            super=None,
            fields=[],
            functions=[],
            bind_map=[]
        )
        result = self.validator.validate_component(comp)
        assert result is True


class TestCValidatorDatamodel:
    """Tests for CValidator with datamodel types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CValidator()

    def test_validate_empty_context(self):
        """Test validating empty context."""
        ctxt = ir.Context(type_m={})
        result = self.validator.validate(ctxt)
        assert result is True

    def test_validate_component_with_no_fields(self):
        """Test validating component with no fields."""
        comp = ir.DataTypeComponent(
            name="TestComp",
            py_type=None,
            super=None,
            fields=[],
            functions=[],
            bind_map=[]
        )
        result = self.validator.validate_component(comp)
        assert result is True

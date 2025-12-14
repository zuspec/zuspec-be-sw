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
import ast
import pytest
from zuspec.dataclasses import dm
from zuspec.be.sw.validator import CValidator, ValidationError


class TestCValidator:
    """Tests for CValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CValidator()

    def test_is_valid_initially(self):
        """Test that validator starts valid."""
        assert self.validator.is_valid()
        assert len(self.validator.errors) == 0

    def test_validate_supported_expr_statement(self):
        """Test validating supported expression statement."""
        code = 'print("Hello")'
        tree = ast.parse(code)
        result = self.validator.validate_ast(tree)
        assert result is True

    def test_validate_supported_assignment(self):
        """Test validating supported assignment."""
        code = 'x = 42'
        tree = ast.parse(code)
        result = self.validator.validate_ast(tree)
        assert result is True

    def test_validate_supported_if(self):
        """Test validating supported if statement."""
        code = 'if x:\n    y = 1'
        tree = ast.parse(code)
        result = self.validator.validate_ast(tree)
        assert result is True

    def test_validate_supported_for(self):
        """Test validating supported for loop."""
        code = 'for i in range(10):\n    x = i'
        tree = ast.parse(code)
        result = self.validator.validate_ast(tree)
        assert result is True

    def test_validate_supported_while(self):
        """Test validating supported while loop."""
        code = 'while x:\n    x -= 1'
        tree = ast.parse(code)
        result = self.validator.validate_ast(tree)
        assert result is True

    def test_validate_supported_return(self):
        """Test validating supported return statement."""
        code = 'return 42'
        tree = ast.parse(code)
        result = self.validator.validate_ast(tree)
        assert result is True

    def test_validate_function_def(self):
        """Test validating function definition."""
        code = '''
def hello():
    print("Hello")
'''
        tree = ast.parse(code)
        # Get the function def
        func_def = tree.body[0]
        result = self.validator.validate_ast(func_def)
        assert result is True

    def test_error_str_with_location(self):
        """Test ValidationError string representation with location."""
        error = ValidationError("Test error", "test.py:10")
        assert "test.py:10" in str(error)
        assert "Test error" in str(error)

    def test_error_str_without_location(self):
        """Test ValidationError string representation without location."""
        error = ValidationError("Test error")
        assert str(error) == "Test error"


class TestCValidatorDatamodel:
    """Tests for CValidator with datamodel types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CValidator()

    def test_validate_empty_context(self):
        """Test validating empty context."""
        ctxt = dm.Context(type_m={})
        result = self.validator.validate(ctxt)
        assert result is True

    def test_validate_component_with_no_fields(self):
        """Test validating component with no fields."""
        comp = dm.DataTypeComponent(
            name="TestComp",
            py_type=None,
            super=None,
            fields=[],
            functions=[],
            bind_map=[]
        )
        result = self.validator.validate_component(comp)
        assert result is True

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
Unit tests for the expr_generator module.
"""
import ast
import pytest
from zuspec.be.sw.expr_generator import ExprGenerator


class TestExprGenerator:
    """Tests for ExprGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.gen = ExprGenerator()

    def test_constant_string(self):
        """Test generating C code for string constant."""
        tree = ast.parse('"Hello"', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == '"Hello"'

    def test_constant_int(self):
        """Test generating C code for integer constant."""
        tree = ast.parse('42', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == '42'

    def test_constant_bool_true(self):
        """Test generating C code for True."""
        tree = ast.parse('True', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == '1'

    def test_constant_bool_false(self):
        """Test generating C code for False."""
        tree = ast.parse('False', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == '0'

    def test_name_variable(self):
        """Test generating C code for variable reference."""
        tree = ast.parse('x', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == 'x'

    def test_binop_add(self):
        """Test generating C code for addition."""
        tree = ast.parse('a + b', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == '(a + b)'

    def test_binop_mult(self):
        """Test generating C code for multiplication."""
        tree = ast.parse('a * b', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == '(a * b)'

    def test_compare_eq(self):
        """Test generating C code for equality comparison."""
        tree = ast.parse('a == b', mode='eval')
        result = self.gen.generate(tree.body)
        assert '==' in result

    def test_compare_lt(self):
        """Test generating C code for less than comparison."""
        tree = ast.parse('a < b', mode='eval')
        result = self.gen.generate(tree.body)
        assert '<' in result

    def test_unary_not(self):
        """Test generating C code for logical not."""
        tree = ast.parse('not x', mode='eval')
        result = self.gen.generate(tree.body)
        assert '!' in result

    def test_unary_negative(self):
        """Test generating C code for negation."""
        tree = ast.parse('-x', mode='eval')
        result = self.gen.generate(tree.body)
        assert '-' in result

    def test_attribute_self(self):
        """Test generating C code for self.attr."""
        tree = ast.parse('self.value', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == 'self->value'

    def test_subscript(self):
        """Test generating C code for subscript access."""
        tree = ast.parse('arr[i]', mode='eval')
        result = self.gen.generate(tree.body)
        assert result == 'arr[i]'

    def test_print_call_string(self):
        """Test generating C code for print with string."""
        tree = ast.parse('print("Hello")', mode='eval')
        result = self.gen.generate(tree.body)
        assert 'fprintf' in result
        assert 'stdout' in result
        assert '"Hello' in result

    def test_print_call_variable(self):
        """Test generating C code for print with variable."""
        tree = ast.parse('print(x)', mode='eval')
        result = self.gen.generate(tree.body)
        assert 'fprintf' in result
        assert '%s' in result

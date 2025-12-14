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
Unit tests for the stmt_generator module.
"""
import ast
import pytest
from zuspec.be.sw.stmt_generator import StmtGenerator


class TestStmtGenerator:
    """Tests for StmtGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.gen = StmtGenerator()

    def _parse_stmt(self, code: str) -> ast.stmt:
        """Parse a single statement."""
        tree = ast.parse(code)
        return tree.body[0]

    def test_expr_statement(self):
        """Test generating C code for expression statement."""
        stmt = self._parse_stmt('print("Hello")')
        result = self.gen._gen_stmt(stmt)
        assert 'fprintf' in result
        assert ';' in result

    def test_assign_simple(self):
        """Test generating C code for simple assignment."""
        stmt = self._parse_stmt('x = 42')
        result = self.gen._gen_stmt(stmt)
        assert 'x = 42;' in result

    def test_aug_assign_add(self):
        """Test generating C code for += assignment."""
        stmt = self._parse_stmt('x += 1')
        result = self.gen._gen_stmt(stmt)
        assert 'x += 1;' in result

    def test_aug_assign_sub(self):
        """Test generating C code for -= assignment."""
        stmt = self._parse_stmt('x -= 1')
        result = self.gen._gen_stmt(stmt)
        assert 'x -= 1;' in result

    def test_if_simple(self):
        """Test generating C code for simple if statement."""
        stmt = self._parse_stmt('if x:\n    y = 1')
        result = self.gen._gen_stmt(stmt)
        assert 'if (x)' in result
        assert 'y = 1;' in result
        assert '{' in result
        assert '}' in result

    def test_if_else(self):
        """Test generating C code for if-else statement."""
        stmt = self._parse_stmt('if x:\n    y = 1\nelse:\n    y = 2')
        result = self.gen._gen_stmt(stmt)
        assert 'if (x)' in result
        assert 'else' in result
        assert 'y = 1;' in result
        assert 'y = 2;' in result

    def test_for_range_single_arg(self):
        """Test generating C code for for range(n) loop."""
        stmt = self._parse_stmt('for i in range(10):\n    x = i')
        result = self.gen._gen_stmt(stmt)
        assert 'for (int i = 0; i < 10; i += 1)' in result
        assert 'x = i;' in result

    def test_for_range_two_args(self):
        """Test generating C code for for range(start, end) loop."""
        stmt = self._parse_stmt('for i in range(1, 10):\n    x = i')
        result = self.gen._gen_stmt(stmt)
        assert 'for (int i = 1; i < 10; i += 1)' in result

    def test_for_range_three_args(self):
        """Test generating C code for for range(start, end, step) loop."""
        stmt = self._parse_stmt('for i in range(0, 10, 2):\n    x = i')
        result = self.gen._gen_stmt(stmt)
        assert 'for (int i = 0; i < 10; i += 2)' in result

    def test_while_loop(self):
        """Test generating C code for while loop."""
        stmt = self._parse_stmt('while x:\n    x -= 1')
        result = self.gen._gen_stmt(stmt)
        assert 'while (x)' in result
        assert 'x -= 1;' in result

    def test_return_value(self):
        """Test generating C code for return with value."""
        stmt = self._parse_stmt('return 42')
        result = self.gen._gen_stmt(stmt)
        assert 'return 42;' in result

    def test_return_none(self):
        """Test generating C code for return without value."""
        stmt = self._parse_stmt('return')
        result = self.gen._gen_stmt(stmt)
        assert 'return;' in result

    def test_break(self):
        """Test generating C code for break."""
        stmt = self._parse_stmt('break')
        result = self.gen._gen_stmt(stmt)
        assert 'break;' in result

    def test_continue(self):
        """Test generating C code for continue."""
        stmt = self._parse_stmt('continue')
        result = self.gen._gen_stmt(stmt)
        assert 'continue;' in result

    def test_pass(self):
        """Test generating C code for pass."""
        stmt = self._parse_stmt('pass')
        result = self.gen._gen_stmt(stmt)
        assert 'pass' in result.lower() or '/*' in result

    def test_generate_multiple_stmts(self):
        """Test generating C code for multiple statements."""
        code = '''
x = 1
y = 2
z = x + y
'''
        tree = ast.parse(code)
        result = self.gen.generate(tree.body)
        assert 'x = 1;' in result
        assert 'y = 2;' in result
        assert 'z = (x + y);' in result

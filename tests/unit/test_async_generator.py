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
Unit tests for async method code generation.
"""
import ast
import pytest
from zuspec.be.sw.async_generator import AsyncMethodGenerator


class TestAsyncMethodGenerator:
    """Tests for AsyncMethodGenerator class."""

    def _parse_async_method(self, code: str) -> ast.AsyncFunctionDef:
        """Parse an async method from code string."""
        tree = ast.parse(code)
        return tree.body[0]

    def test_simple_async_no_await(self):
        """Test async method with no await points."""
        code = '''
async def doit(self):
    x = 1
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        assert "TestComp_doit_task" in result
        assert "switch (idx)" in result
        assert "case 0:" in result
        assert "zsp_timebase_alloc_frame" in result

    def test_async_with_single_await(self):
        """Test async method with single await self.wait()."""
        code = '''
async def doit(self):
    await self.wait(1)
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        assert "case 0:" in result
        assert "case 1:" in result
        assert "zsp_timebase_wait" in result
        assert "ret->idx = 1" in result

    def test_async_with_print_before_await(self):
        """Test async method with print before await."""
        code = '''
async def doit(self):
    print("hello")
    await self.wait(1)
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        assert "fprintf" in result
        assert "hello" in result
        assert "case 0:" in result
        assert "case 1:" in result

    def test_async_with_time_ns(self):
        """Test async method with Time.ns() argument."""
        code = '''
async def doit(self):
    await self.wait(zdc.Time.ns(100))
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        assert "ZSP_TIME_NS(100)" in result

    def test_async_with_time_us(self):
        """Test async method with Time.us() argument."""
        code = '''
async def doit(self):
    await self.wait(zdc.Time.us(50))
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        assert "ZSP_TIME_US(50)" in result

    def test_async_multiple_awaits(self):
        """Test async method with multiple await points."""
        code = '''
async def doit(self):
    print("start")
    await self.wait(1)
    print("middle")
    await self.wait(2)
    print("end")
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        assert "case 0:" in result
        assert "case 1:" in result
        assert "case 2:" in result
        assert "ret->idx = 1" in result
        assert "ret->idx = 2" in result

    def test_generates_wrapper_function(self):
        """Test that wrapper function is generated."""
        code = '''
async def doit(self):
    await self.wait(1)
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        # Should have both task function and wrapper
        assert "TestComp_doit_task" in result
        assert "void TestComp_doit(TestComp *self, zsp_timebase_t *tb)" in result
        assert "zsp_timebase_thread_create" in result

    def test_locals_struct_generated(self):
        """Test that locals struct is generated with self pointer."""
        # Use non-trivial case that requires locals struct
        code = '''
async def doit(self):
    print("hello")
    await self.wait(1)
'''
        func_def = self._parse_async_method(code)
        gen = AsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func_def)
        
        assert "typedef struct {" in result
        assert "TestComp *self;" in result
        assert "} locals_t;" in result


class TestPrintFormatString:
    """Tests for print() with format strings."""

    def test_print_format_string_simple(self):
        """Test print("value: %s" % x) pattern."""
        from zuspec.be.sw.expr_generator import ExprGenerator
        gen = ExprGenerator()
        
        code = 'print("value: %s" % x)'
        tree = ast.parse(code)
        call = tree.body[0].value
        
        result = gen.generate(call)
        assert "fprintf" in result
        assert "value: %s" in result
        assert "x" in result

    def test_print_format_with_method_call(self):
        """Test print("Time: %s" % self.time()) pattern."""
        from zuspec.be.sw.expr_generator import ExprGenerator
        gen = ExprGenerator()
        
        code = 'print("Time: %s" % self.time())'
        tree = ast.parse(code)
        call = tree.body[0].value
        
        result = gen.generate(call)
        assert "fprintf" in result
        assert "Time: %s" in result
        assert "self->time()" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

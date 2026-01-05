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
Unit tests for datamodel-based async method code generation.
"""
import pytest
from zuspec.dataclasses import ir
from zuspec.be.sw.dm_async_generator import DmAsyncMethodGenerator


class TestDmAsyncMethodGenerator:
    """Tests for DmAsyncMethodGenerator class."""

    def test_simple_async_no_await(self):
        """Test async method with no await points."""
        # Create a simple function with just an assignment
        func = ir.Function(
            name="doit",
            is_async=True,
            body=[
                ir.StmtExpr(expr=ir.ExprConstant(value=1))
            ]
        )
        
        gen = DmAsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func)
        
        assert "TestComp_doit_task" in result
        assert "switch (idx)" in result
        assert "case 0:" in result
        assert "zsp_timebase_alloc_frame" in result

    def test_async_with_single_await(self):
        """Test async method with single await self.wait()."""
        # Build: await self.wait(100)
        wait_call = ir.ExprCall(
            func=ir.ExprAttribute(
                value=ir.ExprConstant(value="self"),
                attr="wait"
            ),
            args=[ir.ExprConstant(value=100)]
        )
        await_expr = ir.ExprAwait(value=wait_call)
        
        func = ir.Function(
            name="doit",
            is_async=True,
            body=[
                ir.StmtExpr(expr=await_expr)
            ]
        )
        
        gen = DmAsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func)
        
        assert "case 0:" in result
        assert "case 1:" in result
        assert "zsp_timebase_wait" in result
        assert "ret->idx = 1" in result

    def test_async_with_print_before_await(self):
        """Test async method with print before await."""
        # Build: print("hello"); await self.wait(100)
        print_call = ir.ExprCall(
            func=ir.ExprConstant(value="print"),
            args=[ir.ExprConstant(value="hello")]
        )
        
        wait_call = ir.ExprCall(
            func=ir.ExprAttribute(
                value=ir.ExprConstant(value="self"),
                attr="wait"
            ),
            args=[ir.ExprConstant(value=100)]
        )
        await_expr = ir.ExprAwait(value=wait_call)
        
        func = ir.Function(
            name="doit",
            is_async=True,
            body=[
                ir.StmtExpr(expr=print_call),
                ir.StmtExpr(expr=await_expr)
            ]
        )
        
        gen = DmAsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func)
        
        assert "fprintf" in result
        assert "hello" in result
        assert "case 0:" in result
        assert "case 1:" in result

    def test_async_with_time_ns(self):
        """Test async method with Time.ns() argument."""
        # Build: await self.wait(zdc.Time.ns(100))
        time_call = ir.ExprCall(
            func=ir.ExprAttribute(
                value=ir.ExprAttribute(
                    value=ir.ExprConstant(value="zdc"),
                    attr="Time"
                ),
                attr="ns"
            ),
            args=[ir.ExprConstant(value=100)]
        )
        
        wait_call = ir.ExprCall(
            func=ir.ExprAttribute(
                value=ir.ExprConstant(value="self"),
                attr="wait"
            ),
            args=[time_call]
        )
        await_expr = ir.ExprAwait(value=wait_call)
        
        func = ir.Function(
            name="doit",
            is_async=True,
            body=[
                ir.StmtExpr(expr=await_expr)
            ]
        )
        
        gen = DmAsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func)
        
        assert "ZSP_TIME_NS(100)" in result

    def test_async_multiple_awaits(self):
        """Test async method with multiple await points."""
        # Build: print("start"); await self.wait(1); print("middle"); await self.wait(2); print("end")
        print1 = ir.ExprCall(
            func=ir.ExprConstant(value="print"),
            args=[ir.ExprConstant(value="start")]
        )
        print2 = ir.ExprCall(
            func=ir.ExprConstant(value="print"),
            args=[ir.ExprConstant(value="middle")]
        )
        print3 = ir.ExprCall(
            func=ir.ExprConstant(value="print"),
            args=[ir.ExprConstant(value="end")]
        )
        
        def make_await(delay):
            return ir.ExprAwait(value=ir.ExprCall(
                func=ir.ExprAttribute(
                    value=ir.ExprConstant(value="self"),
                    attr="wait"
                ),
                args=[ir.ExprConstant(value=delay)]
            ))
        
        func = ir.Function(
            name="doit",
            is_async=True,
            body=[
                ir.StmtExpr(expr=print1),
                ir.StmtExpr(expr=make_await(1)),
                ir.StmtExpr(expr=print2),
                ir.StmtExpr(expr=make_await(2)),
                ir.StmtExpr(expr=print3),
            ]
        )
        
        gen = DmAsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func)
        
        assert "case 0:" in result
        assert "case 1:" in result
        assert "case 2:" in result
        assert "ret->idx = 1" in result
        assert "ret->idx = 2" in result

    def test_generates_wrapper_function(self):
        """Test that wrapper function is generated."""
        func = ir.Function(
            name="doit",
            is_async=True,
            body=[
                ir.StmtExpr(expr=ir.ExprAwait(value=ir.ExprCall(
                    func=ir.ExprAttribute(
                        value=ir.ExprConstant(value="self"),
                        attr="wait"
                    ),
                    args=[ir.ExprConstant(value=1)]
                )))
            ]
        )
        
        gen = DmAsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func)
        
        # Should have both task function and wrapper
        assert "TestComp_doit_task" in result
        assert "void TestComp_doit(TestComp *self, zsp_timebase_t *tb)" in result
        assert "zsp_timebase_thread_create" in result

    def test_print_with_format_string(self):
        """Test print("format %s" % value) pattern."""
        # Build: print("value: %s" % x)
        format_expr = ir.ExprBin(
            lhs=ir.ExprConstant(value="value: %s"),
            op=ir.BinOp.Mod,
            rhs=ir.ExprConstant(value="x")
        )
        print_call = ir.ExprCall(
            func=ir.ExprConstant(value="print"),
            args=[format_expr]
        )
        
        func = ir.Function(
            name="doit",
            is_async=True,
            body=[
                ir.StmtExpr(expr=print_call)
            ]
        )
        
        gen = DmAsyncMethodGenerator("TestComp", "doit")
        result = gen.generate(func)
        
        assert "fprintf" in result
        assert "value: %s" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

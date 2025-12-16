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
Integration test for async-to-sync conversion in code generation.
"""
import pytest
import tempfile
from pathlib import Path
from zuspec.dataclasses import dm
from zuspec.be.sw.c_generator import CGenerator
from zuspec.be.sw.async_analyzer import AsyncAnalyzer


class TestAsyncToSyncConversion:
    """Tests for async-to-sync conversion during code generation."""
    
    def test_generates_both_sync_and_async_variants(self):
        """Test that convertible async functions generate both variants."""
        # Create a simple async function without await
        stmt = dm.StmtReturn(value=dm.ExprConstant(value=42))
        func = dm.Function(
            name="get_value",
            is_async=True,
            body=[stmt],
            returns=dm.DataTypeInt(bits=32, signed=True)
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = dm.Context()
        ctxt.type_m["TestComp"] = comp
        
        # Generate C code
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = CGenerator(Path(tmpdir))
            files = gen.generate(ctxt)
            
            # Check that both sync and async variants are generated
            impl_file = Path(tmpdir) / "testcomp.c"
            assert impl_file.exists()
            
            content = impl_file.read_text()
            
            # Should have sync variant
            assert "TestComp_get_value_sync" in content
            assert "static inline int32_t TestComp_get_value_sync" in content
            
            # Should also have async variant for compatibility
            assert "TestComp_get_value_task" in content
    
    def test_async_with_await_only_generates_async(self):
        """Test that functions with await only generate async variant."""
        # Create async function with await self.wait()
        # Build: await self.wait(time_value)
        wait_call = dm.ExprCall(
            func=dm.ExprAttribute(
                value=dm.TypeExprRefSelf(),
                attr="wait"
            ),
            args=[dm.ExprConstant(value=100)]
        )
        await_expr = dm.ExprAwait(value=wait_call)
        stmt = dm.StmtExpr(expr=await_expr)
        func = dm.Function(
            name="wait_func",
            is_async=True,
            body=[stmt]
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = dm.Context()
        ctxt.type_m["TestComp"] = comp
        
        # Generate C code
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = CGenerator(Path(tmpdir))
            files = gen.generate(ctxt)
            
            impl_file = Path(tmpdir) / "testcomp.c"
            assert impl_file.exists()
            
            content = impl_file.read_text()
            
            # Should NOT have sync variant
            assert "TestComp_wait_func_sync" not in content
            
            # Should have async variant
            assert "TestComp_wait_func_task" in content
    
    def test_header_declares_both_variants(self):
        """Test that header declares both sync and async variants."""
        # Create simple async function without await
        stmt = dm.StmtReturn(value=dm.ExprConstant(value=42))
        func = dm.Function(
            name="get_value",
            is_async=True,
            body=[stmt],
            returns=dm.DataTypeInt(bits=32, signed=True)
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = dm.Context()
        ctxt.type_m["TestComp"] = comp
        
        # Generate C code
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = CGenerator(Path(tmpdir))
            files = gen.generate(ctxt)
            
            header_file = Path(tmpdir) / "testcomp.h"
            assert header_file.exists()
            
            content = header_file.read_text()
            
            # Should declare sync variant
            assert "TestComp_get_value_sync" in content
            
            # Should declare async variant
            assert "void TestComp_get_value(" in content
    
    def test_analyzer_report_printed(self, capsys):
        """Test that analyzer report is printed during generation."""
        # Create simple async function
        stmt = dm.StmtReturn(value=dm.ExprConstant(value=42))
        func = dm.Function(
            name="get_value",
            is_async=True,
            body=[stmt]
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = dm.Context()
        ctxt.type_m["TestComp"] = comp
        
        # Generate C code
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = CGenerator(Path(tmpdir))
            gen.generate(ctxt)
            
            # Check that report was printed
            captured = capsys.readouterr()
            assert "Async-to-Sync Conversion Analysis Report" in captured.out
            assert "TestComp.get_value" in captured.out
    
    def test_external_task_never_converted(self):
        """Test that external tasks (in protocols) are never converted."""
        # Create a protocol method (external interface)
        func = dm.Function(
            name="external_method",
            is_async=True,
            body=[]
        )
        
        proto = dm.DataTypeProtocol(
            name="ExternalAPI",
            methods=[func]
        )
        
        ctxt = dm.Context()
        ctxt.type_m["ExternalAPI"] = proto
        
        # Analyze
        analyzer = AsyncAnalyzer(ctxt)
        analyzer.analyze()
        
        # External task should be identified and NOT convertible
        assert "ExternalAPI.external_method" in analyzer.external_tasks
        assert not analyzer.is_sync_convertible("ExternalAPI", "external_method")

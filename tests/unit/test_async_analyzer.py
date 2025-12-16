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
Unit tests for async-to-sync conversion analyzer.
"""
import pytest
from zuspec.dataclasses import dm
from zuspec.be.sw.async_analyzer import AsyncAnalyzer


class TestAsyncAnalyzer:
    """Tests for AsyncAnalyzer class."""
    
    def _create_context_with_component(self, comp: dm.DataTypeComponent) -> dm.Context:
        """Create a context with a single component."""
        ctxt = dm.Context()
        ctxt.type_m[comp.name] = comp
        return ctxt
    
    def test_empty_async_function_convertible(self):
        """Test that empty async function can be converted to sync."""
        func = dm.Function(
            name="empty_func",
            is_async=True,
            body=[]
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = self._create_context_with_component(comp)
        analyzer = AsyncAnalyzer(ctxt)
        results = analyzer.analyze()
        
        assert "TestComp.empty_func" in results
        assert results["TestComp.empty_func"] is True
    
    def test_async_function_with_await_not_convertible(self):
        """Test that async function with await cannot be converted."""
        # Create an await expression
        await_expr = dm.ExprAwait(value=dm.ExprConstant(value=1))
        stmt = dm.StmtExpr(expr=await_expr)
        
        func = dm.Function(
            name="async_func",
            is_async=True,
            body=[stmt]
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = self._create_context_with_component(comp)
        analyzer = AsyncAnalyzer(ctxt)
        results = analyzer.analyze()
        
        assert "TestComp.async_func" in results
        assert results["TestComp.async_func"] is False
    
    def test_async_function_without_await_convertible(self):
        """Test that async function without await can be converted."""
        # Simple assignment statement
        stmt = dm.StmtAssign(
            targets=[dm.ExprRefLocal(name="x")],
            value=dm.ExprConstant(value=42)
        )
        
        func = dm.Function(
            name="sync_func",
            is_async=True,
            body=[stmt]
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = self._create_context_with_component(comp)
        analyzer = AsyncAnalyzer(ctxt)
        results = analyzer.analyze()
        
        assert "TestComp.sync_func" in results
        assert results["TestComp.sync_func"] is True
    
    def test_external_task_not_convertible(self):
        """Test that external tasks (import/export) are never converted."""
        func = dm.Function(
            name="external_method",
            is_async=True,
            body=[]
        )
        
        # Create a protocol (external interface)
        proto = dm.DataTypeProtocol(
            name="ExternalAPI",
            methods=[func]
        )
        
        ctxt = dm.Context()
        ctxt.type_m["ExternalAPI"] = proto
        
        analyzer = AsyncAnalyzer(ctxt)
        results = analyzer.analyze()
        
        # External tasks should be identified
        assert "ExternalAPI.external_method" in analyzer.external_tasks
    
    def test_get_report_format(self):
        """Test that report generation works."""
        func = dm.Function(
            name="test_func",
            is_async=True,
            body=[]
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = self._create_context_with_component(comp)
        analyzer = AsyncAnalyzer(ctxt)
        analyzer.analyze()
        
        report = analyzer.get_report()
        
        assert "Async-to-Sync Conversion Analysis Report" in report
        assert "Total async functions analyzed:" in report
        assert "TestComp.test_func" in report
    
    def test_is_sync_convertible_api(self):
        """Test the convenience API for checking convertibility."""
        func = dm.Function(
            name="test_func",
            is_async=True,
            body=[]
        )
        
        comp = dm.DataTypeComponent(
            name="TestComp",
            super=None,
            functions=[func]
        )
        
        ctxt = self._create_context_with_component(comp)
        analyzer = AsyncAnalyzer(ctxt)
        analyzer.analyze()
        
        assert analyzer.is_sync_convertible("TestComp", "test_func") is True
        assert analyzer.is_sync_convertible("TestComp", "nonexistent") is False

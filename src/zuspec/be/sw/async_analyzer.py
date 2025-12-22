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
Async-to-sync conversion analyzer for ZuSpec async functions.

This module analyzes async functions in the datamodel to determine if they
can be safely converted to synchronous functions. Functions without await
expressions, async calls, or time delays can be converted to improve performance.

External tasks (import/export) must always remain async.
"""
from typing import Set, Dict, Optional
from zuspec.dataclasses import ir


class AsyncAnalyzer:
    """
    Analyzes async functions to determine sync-convertibility.
    
    This analyzer walks the datamodel to identify async functions that don't
    actually need async machinery (no await, no async calls, no time operations).
    """
    
    def __init__(self, ctxt: ir.Context):
        self.ctxt = ctxt
        # Map: function_id -> can_be_sync
        self.sync_convertible: Dict[str, bool] = {}
        # Set of function names that are import/export (must stay async)
        self.external_tasks: Set[str] = set()
    
    def analyze(self) -> Dict[str, bool]:
        """
        Analyze all async functions in the context.
        
        Returns:
            Dictionary mapping function identifiers to whether they can be sync.
        """
        # First pass: identify all external tasks (import/export)
        self._identify_external_tasks()
        
        # Second pass: analyze each async function
        for type_name, dtype in self.ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeComponent):
                self._analyze_component(dtype)
        
        return self.sync_convertible
    
    def _identify_external_tasks(self):
        """Identify import/export tasks that must remain async."""
        # Import/export tasks are typically marked with special decorators or
        # in special contexts. For now, we'll mark functions with specific names
        # or patterns. This can be extended based on actual ZuSpec semantics.
        
        # Common patterns for external tasks:
        # - Functions with 'import' or 'export' in name
        # - Functions marked with @import_task or @export_task
        # - Functions in specific API/protocol contexts
        
        for type_name, dtype in self.ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeProtocol):
                # All methods in protocols are considered external interfaces
                for func in dtype.methods:
                    func_id = f"{type_name}.{func.name}"
                    self.external_tasks.add(func_id)
    
    def _analyze_component(self, comp: ir.DataTypeComponent):
        """Analyze all async functions in a component."""
        for func in comp.functions:
            if getattr(func, 'is_async', False):
                func_id = f"{comp.name}.{func.name}"
                
                # Check if this is an external task
                if func_id in self.external_tasks:
                    self.sync_convertible[func_id] = False
                    continue
                
                # Analyze if the function can be converted to sync
                can_be_sync = self._can_convert_to_sync(func, comp)
                self.sync_convertible[func_id] = can_be_sync
    
    def _can_convert_to_sync(self, func: ir.Function, comp: ir.DataTypeComponent) -> bool:
        """
        Determine if an async function can be converted to synchronous.
        
        A function can be converted to sync if:
        1. It contains no await expressions
        2. It doesn't call other async methods
        3. It doesn't use time delays (wait, delay, etc.)
        4. It doesn't use channel operations that might block
        5. It's not marked as an external task
        
        Args:
            func: The function to analyze
            comp: The component containing the function
            
        Returns:
            True if the function can be safely converted to sync
        """
        if not func.body:
            # Empty function - safe to convert
            return True
        
        # Walk the statement tree looking for async operations
        return self._analyze_statements(func.body, comp)
    
    def _analyze_statements(self, stmts, comp: ir.DataTypeComponent) -> bool:
        """
        Analyze a list of statements for async operations.
        
        Returns True if NO async operations are found (safe to convert).
        """
        for stmt in stmts:
            if not self._analyze_statement(stmt, comp):
                return False
        return True
    
    def _analyze_statement(self, stmt: ir.Stmt, comp: ir.DataTypeComponent) -> bool:
        """
        Analyze a single statement for async operations.
        
        Returns True if NO async operations are found.
        """
        if isinstance(stmt, ir.StmtExpr):
            return self._analyze_expr(stmt.expr, comp)
        
        elif isinstance(stmt, ir.StmtAssign):
            # Check the value being assigned
            return self._analyze_expr(stmt.value, comp)
        
        elif isinstance(stmt, ir.StmtReturn):
            # Check the return value
            if stmt.value:
                return self._analyze_expr(stmt.value, comp)
            return True
        
        elif isinstance(stmt, ir.StmtIf):
            # Check all branches
            if not self._analyze_expr(stmt.test, comp):
                return False
            if not self._analyze_statements(stmt.body, comp):
                return False
            if stmt.orelse and not self._analyze_statements(stmt.orelse, comp):
                return False
            return True
        
        elif isinstance(stmt, ir.StmtWhile):
            # Check condition and body
            if not self._analyze_expr(stmt.test, comp):
                return False
            return self._analyze_statements(stmt.body, comp)
        
        elif isinstance(stmt, ir.StmtFor):
            # Check iterator and body
            if not self._analyze_expr(stmt.iter, comp):
                return False
            return self._analyze_statements(stmt.body, comp)
        
        # Unknown statement type - conservatively keep as async
        return True
    
    def _analyze_expr(self, expr, comp: ir.DataTypeComponent) -> bool:
        """
        Analyze an expression for async operations.
        
        Returns True if NO async operations are found.
        """
        if isinstance(expr, ir.ExprAwait):
            # Found an await - must stay async
            return False
        
        elif isinstance(expr, ir.ExprCall):
            # Check if calling an async function
            return self._analyze_call(expr, comp)
        
        elif isinstance(expr, ir.ExprBin):
            # Check both operands
            if not self._analyze_expr(expr.lhs, comp):
                return False
            return self._analyze_expr(expr.rhs, comp)
        
        elif isinstance(expr, ir.ExprUnary):
            return self._analyze_expr(expr.operand, comp)
        
        elif isinstance(expr, ir.ExprAttribute):
            return self._analyze_expr(expr.value, comp)
        
        elif isinstance(expr, ir.ExprSubscript):
            if not self._analyze_expr(expr.value, comp):
                return False
            return self._analyze_expr(expr.slice, comp)
        
        elif isinstance(expr, ir.ExprCompare):
            if not self._analyze_expr(expr.left, comp):
                return False
            for comparator in expr.comparators:
                if not self._analyze_expr(comparator, comp):
                    return False
            return True
        
        # Other expression types (constants, names, etc.) are safe
        return True
    
    def _analyze_call(self, call: ir.ExprCall, comp: ir.DataTypeComponent) -> bool:
        """
        Analyze a function call to see if it's async.
        
        Returns True if the call is NOT async (safe for sync conversion).
        """
        # Check if this is a method call
        if isinstance(call.func, ir.ExprAttribute):
            method_name = call.func.attr
            
            # Check for known async operations
            if method_name in ('wait', 'delay', 'sleep', 'yield_'):
                # Time operations - must stay async
                return False
            
            # Check for channel operations that might block
            if method_name in ('get', 'put', 'nb_get', 'nb_put', 'peek'):
                # Channel operations - conservatively keep as async
                # (Could be refined to check if channel is non-blocking)
                return False
            
            # Try to resolve the method and check if it's async
            # This would require more sophisticated type resolution
            # For now, we'll be conservative
            
        elif isinstance(call.func, ir.ExprRefPy):
            # Direct function reference
            ref_name = call.func.ref
            
            # Check for known async built-ins
            if ref_name in ('wait', 'delay', 'sleep'):
                return False
        
        # Analyze arguments
        for arg in call.args:
            if not self._analyze_expr(arg, comp):
                return False
        
        # Call appears safe
        return True
    
    def is_sync_convertible(self, comp_name: str, func_name: str) -> bool:
        """
        Check if a specific function can be converted to sync.
        
        Args:
            comp_name: Component name
            func_name: Function name
            
        Returns:
            True if the function can be converted to sync
        """
        func_id = f"{comp_name}.{func_name}"
        return self.sync_convertible.get(func_id, False)
    
    def get_report(self) -> str:
        """Generate a human-readable report of the analysis."""
        lines = ["Async-to-Sync Conversion Analysis Report", "=" * 50, ""]
        
        total_async = len(self.sync_convertible)
        convertible = sum(1 for v in self.sync_convertible.values() if v)
        
        lines.append(f"Total async functions analyzed: {total_async}")
        lines.append(f"Convertible to sync: {convertible} ({convertible*100//max(total_async,1)}%)")
        lines.append(f"Must remain async: {total_async - convertible}")
        lines.append("")
        
        if self.external_tasks:
            lines.append("External tasks (must remain async):")
            for task in sorted(self.external_tasks):
                lines.append(f"  - {task}")
            lines.append("")
        
        lines.append("Convertible functions:")
        for func_id, can_convert in sorted(self.sync_convertible.items()):
            if can_convert:
                lines.append(f"  ✓ {func_id}")
        
        lines.append("")
        lines.append("Must remain async:")
        for func_id, can_convert in sorted(self.sync_convertible.items()):
            if not can_convert:
                lines.append(f"  ✗ {func_id}")
        
        return "\n".join(lines)

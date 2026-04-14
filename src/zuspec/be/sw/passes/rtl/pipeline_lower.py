"""
PipelineLowerPass — lower @stage pipeline methods to inline C.

For pipeline components (those with ``stage_method_irs``), this pass:
  1. Walks each stage's Python AST body to discover writes to ``self.*``
     and adds those field names to ``ctx.rtl_nxt_fields``.
  2. Generates inline C code for the entire pipeline (stages in order)
     and stores it in ``ctx.rtl_pipeline_clock_body``.

``CEmitPass`` uses ``ctx.rtl_pipeline_clock_body`` when emitting
``<Name>_clock_edge()`` if this list is non-empty.
"""
from __future__ import annotations

import ast
from typing import Dict, List, Set

from zuspec.dataclasses.ir.data_type import DataTypeInt

from zuspec.be.sw.ir.base import SwContext
from .type_mapper import RtlTypeMapper
from .ast_lower import ASTLower


def _get_c_type(stage_output_annotation) -> str:
    """Return C type string for a stage output port annotation."""
    try:
        import typing
        args = typing.get_args(stage_output_annotation)
        if args:
            width_obj = args[0] if not isinstance(args[0], type) else None
            if width_obj is not None and hasattr(width_obj, 'width'):
                tm = RtlTypeMapper()
                from zuspec.dataclasses.ir.data_type import DataTypeInt as DTI
                dt = DTI(bits=width_obj.width, signed=getattr(width_obj, 'signed', False))
                return tm.map_rtl_int_type(dt)
    except Exception:
        pass
    return "uint64_t"


class PipelineLowerPass:
    """Lower pipeline stage ASTs and populate ctx.rtl_pipeline_clock_body."""

    def run(self, ctx: SwContext) -> SwContext:
        comp = ctx.rtl_component
        stages = getattr(comp, "stage_method_irs", [])
        if not stages:
            return ctx

        # Build field lookup dict
        fields_by_name = {f.name: f for f in comp.fields}
        tm = RtlTypeMapper()

        # Get module globals from the original stage method for name resolution
        # (e.g. ACCUM_MAX). We use the component class's module globals via its
        # body_ast — the function is compiled from the original source so its
        # closure globals are available on the original uncompiled class.
        module_globals = self._get_module_globals(comp, ctx)

        # Pipeline clock body lines (will wrap in clock_edge in CEmitPass)
        body_lines: List[str] = []
        indent = "    "

        # Inter-stage variable declarations (output vars from previous stage)
        inter_vars: Dict[str, str] = {}  # var_name → c_type

        for stage in stages:
            fn_node = stage.body_ast

            # Determine output variable names and types for this stage
            out_specs = stage.outputs
            out_vars: List[str] = []
            for spec in out_specs:
                # Determine output var names (one per element in the annotation tuple)
                ann = spec.annotation_ast
                if isinstance(ann, tuple):
                    for i, a in enumerate(ann):
                        var_name = f"_s{stage.name}_out{i}"
                        c_type = _get_c_type(a)
                        out_vars.append(var_name)
                        inter_vars[var_name] = c_type
                elif ann == ():
                    pass  # no outputs
                else:
                    var_name = f"_s{stage.name}_out0"
                    c_type = _get_c_type(ann)
                    out_vars.append(var_name)
                    inter_vars[var_name] = c_type

            # Map stage input names → already-declared C variable names
            # Inputs to this stage come from the previous stage's outputs
            # or from the pipeline's execute() method ordering.
            # Heuristic: use the stage's PortSpec names to rename inter_vars.
            var_renames: Dict[str, str] = {}
            if stage.inputs:
                # Match inputs positionally to last stage's outputs
                prev_stage_idx = stages.index(stage) - 1
                if prev_stage_idx >= 0:
                    prev_stage = stages[prev_stage_idx]
                    prev_out_vars = [
                        f"_s{prev_stage.name}_out{i}"
                        for i in range(len(prev_stage.outputs[0].annotation_ast)
                                       if prev_stage.outputs and
                                          isinstance(prev_stage.outputs[0].annotation_ast, tuple)
                                       else 0)
                    ]
                    for inp, pvar in zip(stage.inputs, prev_out_vars):
                        var_renames[inp.name] = pvar

            # Emit declarations for output vars before calling the lowerer
            for var_name in out_vars:
                c_type = inter_vars[var_name]
                body_lines.append(f"{indent}{c_type} {var_name} = 0;")

            # Lower the stage body
            lowerer = ASTLower(
                fields_by_name=fields_by_name,
                nxt_fields=ctx.rtl_nxt_fields,  # mutated in place
                module_globals=module_globals,
                type_mapper=tm,
            )
            # Apply input renames to the lowerer's locals so Name refs resolve
            for inp_name, c_var in var_renames.items():
                lowerer._locals[inp_name] = inter_vars.get(c_var, "uint64_t")

            stage_lines = lowerer.lower_function(fn_node, out_vars, indent=indent)

            # Patch stage input Name references to use the renamed C vars
            if var_renames:
                patched = []
                for line in stage_lines:
                    for inp_name, c_var in var_renames.items():
                        # Replace bare `inp_name` references (not inside identifiers)
                        import re
                        line = re.sub(r'\b' + re.escape(inp_name) + r'\b', c_var, line)
                    patched.append(line)
                stage_lines = patched

            body_lines.extend(stage_lines)

        ctx.rtl_pipeline_clock_body = body_lines
        return ctx

    def _get_module_globals(self, comp, ctx: SwContext) -> dict:
        """Best-effort: extract module globals for constant resolution."""
        # Try to get globals from the component class if it's still accessible
        try:
            import sys
            for mod in sys.modules.values():
                if hasattr(mod, comp.name):
                    cls = getattr(mod, comp.name)
                    if hasattr(cls, '__module__'):
                        mod2 = sys.modules.get(cls.__module__, mod)
                        return vars(mod2)
        except Exception:
            pass
        return {}

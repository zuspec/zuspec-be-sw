"""ElaborateSwPass — builds SwCompInst tree and populates SwContext.inst_m."""
from __future__ import annotations

import dataclasses as dc
from typing import List, Optional, Any, Dict

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwNode, SwContext
from zuspec.be.sw.pipeline import SwPass


@dc.dataclass(kw_only=True)
class SwCompInst(SwNode):
    """One instantiated component in the component hierarchy.

    Attributes
    ----------
    type_name:
        Name of the ``DataTypeComponent`` that this instance represents.
    inst_path:
        Dot-separated path from the root, e.g. ``"rv_core.alu_pool"``.
    dtype:
        The ``DataTypeComponent`` being instantiated.
    children:
        Nested ``SwCompInst`` objects for sub-component fields.
    active:
        ``False`` when the component has been pruned by config.
    """
    type_name: str = dc.field(default="")
    inst_path: str = dc.field(default="")
    dtype: Optional[ir.DataTypeComponent] = dc.field(default=None)
    children: List["SwCompInst"] = dc.field(default_factory=list)
    active: bool = dc.field(default=True)


class ElaborateSwPass(SwPass):
    """Populate ``SwContext.inst_m`` by instantiating all components.

    The pass finds the top-level ``DataTypeComponent`` (configurable via
    ``config.get("top")``) and recursively instantiates all sub-component
    fields.  The resulting ``SwCompInst`` tree is stored in
    ``ctxt.root_inst`` and every instance is also indexed by its dot-path
    in ``ctxt.inst_m``.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}

    def run(self, ctxt: SwContext) -> SwContext:
        top_type = self._find_top(ctxt)
        if top_type is None:
            return ctxt

        root_name = top_type.name or "top"
        root_inst = self._instantiate(top_type, root_name.lower(), ctxt)
        ctxt.root_inst = root_inst
        return ctxt

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_top(self, ctxt: SwContext) -> Optional[ir.DataTypeComponent]:
        """Return the top-level component type.

        If ``config["top"]`` names a type, use that.  Otherwise, if there is
        exactly one ``DataTypeComponent`` in the context, use it.
        """
        top_name = self._config.get("top")
        components = [
            dtype
            for dtype in ctxt.type_m.values()
            if isinstance(dtype, ir.DataTypeComponent)
        ]

        if top_name:
            for comp in components:
                if comp.name == top_name:
                    return comp
            return None

        if len(components) == 1:
            return components[0]

        # Multiple components — try to find the one that is not referenced
        # as a field of any other component (i.e., the structural root).
        referenced: set = set()
        for comp in components:
            for field in comp.fields:
                ft = field.datatype
                if isinstance(ft, ir.DataTypeRef):
                    referenced.add(ft.ref_name)
                elif isinstance(ft, ir.DataTypeComponent) and ft.name:
                    referenced.add(ft.name)

        roots = [c for c in components if c.name not in referenced]
        if len(roots) == 1:
            return roots[0]

        # Fall back to the last defined component.
        return components[-1] if components else None

    def _instantiate(
        self,
        dtype: ir.DataTypeComponent,
        inst_path: str,
        ctxt: SwContext,
    ) -> SwCompInst:
        inst = SwCompInst(
            type_name=dtype.name or "",
            inst_path=inst_path,
            dtype=dtype,
        )
        ctxt.inst_m[inst_path] = inst

        for field in dtype.fields:
            field_dtype = self._resolve_type(field.datatype, ctxt)
            if isinstance(field_dtype, ir.DataTypeComponent):
                child_path = f"{inst_path}.{field.name}"
                child = self._instantiate(field_dtype, child_path, ctxt)
                inst.children.append(child)

        return inst

    def _resolve_type(
        self, dtype: ir.DataType, ctxt: SwContext
    ) -> ir.DataType:
        """Resolve a ``DataTypeRef`` to its concrete type via ``ctxt.type_m``."""
        if isinstance(dtype, ir.DataTypeRef):
            resolved = ctxt.type_m.get(dtype.ref_name)
            return resolved if resolved is not None else dtype
        return dtype

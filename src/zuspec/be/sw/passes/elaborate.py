"""ElaborateSwPass — builds SwCompInst tree and populates SwContext.inst_m."""
from __future__ import annotations

import dataclasses as dc
from typing import List, Optional, Any, Dict

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwNode, SwContext, SwConnection
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

        # Walk all component types and elaborate their __bind__ maps.
        for type_name, dtype in ctxt.type_m.items():
            if isinstance(dtype, ir.DataTypeComponent):
                self._elaborate_binds(dtype, ctxt)

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

    # ------------------------------------------------------------------
    # __bind__ elaboration
    # ------------------------------------------------------------------

    def _elaborate_binds(
        self, comp: ir.DataTypeComponent, ctxt: SwContext
    ) -> None:
        """Decode bind_map entries in *comp* and append to ``ctxt.connections``."""
        if not comp.bind_map:
            return

        comp_fields = list(comp.fields)

        for bind in comp.bind_map:
            conn = self._decode_bind(bind, comp, comp_fields, ctxt)
            if conn is not None:
                ctxt.connections.append(conn)

    def _decode_bind(
        self,
        bind: ir.Bind,
        owner: ir.DataTypeComponent,
        owner_fields: List[ir.Field],
        ctxt: SwContext,
    ) -> Optional[SwConnection]:
        """Decode a single ``Bind`` into a ``SwConnection``.

        The bind uses ``ExprRefField`` nesting:
          lhs = ExprRefField(base=ExprRefField(base=TypeExprRefSelf, index=<sub_idx>), index=<port_idx>)
          rhs = ExprRefField(base=ExprRefField(base=TypeExprRefSelf, index=<sub_idx>), index=<export_idx>)
        """
        lhs = bind.lhs
        rhs = bind.rhs

        # Both must be double-nested ExprRefField
        if not (isinstance(lhs, ir.ExprRefField) and isinstance(rhs, ir.ExprRefField)):
            return None
        if not (isinstance(lhs.base, ir.ExprRefField) and isinstance(rhs.base, ir.ExprRefField)):
            return None

        try:
            # Decode port side (lhs)
            port_sub_field = owner_fields[lhs.base.index]
            port_sub_type = self._resolve_type(port_sub_field.datatype, ctxt)
            if not isinstance(port_sub_type, ir.DataTypeComponent):
                return None
            port_sub_fields = list(port_sub_type.fields)
            port_field = port_sub_fields[lhs.index]

            # Decode export side (rhs)
            exp_sub_field = owner_fields[rhs.base.index]
            exp_sub_type = self._resolve_type(exp_sub_field.datatype, ctxt)
            if not isinstance(exp_sub_type, ir.DataTypeComponent):
                return None
            exp_sub_fields = list(exp_sub_type.fields)
            exp_field = exp_sub_fields[rhs.index]

            # Resolve the shared protocol type
            protocol = self._resolve_type(port_field.datatype, ctxt)
            if not isinstance(protocol, ir.DataTypeProtocol):
                protocol = self._resolve_type(exp_field.datatype, ctxt)

            owner_name = owner.name or ""
            return SwConnection(
                initiator_component=port_sub_type.name or "",
                initiator_port=port_field.name,
                initiator_inst_path=f"{owner_name.lower()}.{port_sub_field.name}",
                target_component=exp_sub_type.name or "",
                target_export=exp_field.name,
                target_inst_path=f"{owner_name.lower()}.{exp_sub_field.name}",
                protocol=protocol if isinstance(protocol, ir.DataTypeProtocol) else None,
            )
        except (IndexError, AttributeError):
            return None

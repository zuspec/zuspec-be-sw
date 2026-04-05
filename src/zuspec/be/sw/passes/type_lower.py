"""TypeLowerPass — maps every DataType to a canonical C type string."""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.pipeline import SwPass


class TypeLowerPass(SwPass):
    """Populate ``SwContext.c_type_m`` and ``SwContext.c_type_bodies``.

    Promotes the logic from ``TypeMapper.map_type`` into a proper pass so
    that downstream passes can look up ``ctxt.c_type_m[name]`` without
    repeating mapping logic.  ``TypeMapper`` remains as a thin wrapper for
    backward compatibility.
    """

    INT_MAP: Dict[Tuple[int, bool], str] = {
        (8, True): "int8_t",
        (8, False): "uint8_t",
        (16, True): "int16_t",
        (16, False): "uint16_t",
        (32, True): "int32_t",
        (32, False): "uint32_t",
        (64, True): "int64_t",
        (64, False): "uint64_t",
    }

    def run(self, ctxt: SwContext) -> SwContext:
        # Compute topological order so that struct bodies refer to already
        # declared types wherever possible.
        ordered = self._topological_sort(ctxt.type_m)

        for dtype in ordered:
            name = dtype.name
            if name is None:
                continue
            c_type = self._map_type(dtype, ctxt)
            if c_type:
                ctxt.c_type_m[name] = c_type
            body = self._type_body(dtype, ctxt)
            if body:
                ctxt.c_type_bodies[name] = body

        return ctxt

    # ------------------------------------------------------------------
    # Type mapping
    # ------------------------------------------------------------------

    def _map_type(self, dtype: ir.DataType, ctxt: SwContext) -> Optional[str]:
        if isinstance(dtype, ir.DataTypeInt):
            return self._map_int(dtype)
        if isinstance(dtype, ir.DataTypeUptr):
            return "uintptr_t"
        if isinstance(dtype, ir.DataTypeChandle):
            return "void *"
        if isinstance(dtype, ir.DataTypeString):
            return "const char *"
        if isinstance(dtype, ir.DataTypeEnum):
            return f"{dtype.name}_t"
        if isinstance(dtype, ir.DataTypeStruct):
            return f"{dtype.name}_t"
        if isinstance(dtype, ir.DataTypeComponent):
            return f"{dtype.name}_t"
        if isinstance(dtype, ir.DataTypeArray):
            elem_c = self._resolve_elem(dtype.element_type, ctxt)
            return f"{elem_c}"  # caller appends [N]
        if isinstance(dtype, ir.DataTypeList):
            return "zsp_list_t"
        if isinstance(dtype, ir.DataTypeChannel):
            return "zsp_fifo_t"
        if isinstance(dtype, ir.DataTypeGetIF):
            return "zsp_get_if_t"
        if isinstance(dtype, ir.DataTypePutIF):
            return "zsp_put_if_t"
        if isinstance(dtype, ir.DataTypeAddressSpace):
            return "zsp_addr_space_t *"
        if isinstance(dtype, ir.DataTypeAddrHandle):
            return "uintptr_t"
        if isinstance(dtype, ir.DataTypeRef):
            resolved = ctxt.type_m.get(dtype.ref_name)
            if resolved:
                return self._map_type(resolved, ctxt)
            return f"{dtype.ref_name}_t"
        return None

    def _map_int(self, dtype: ir.DataTypeInt) -> str:
        bits = dtype.bits
        signed = dtype.signed
        if bits < 0:
            bits = 32
        key = (bits, signed)
        if key in self.INT_MAP:
            return self.INT_MAP[key]
        # Round up to next standard size
        for sz in (8, 16, 32, 64):
            if bits <= sz:
                return f"{'int' if signed else 'uint'}{sz}_t"
        return "uint64_t"

    def _resolve_elem(self, dtype: Optional[ir.DataType], ctxt: SwContext) -> str:
        if dtype is None:
            return "uint8_t"
        c = self._map_type(dtype, ctxt)
        return c or "uint8_t"

    # ------------------------------------------------------------------
    # Type body generation
    # ------------------------------------------------------------------

    def _type_body(self, dtype: ir.DataType, ctxt: SwContext) -> Optional[str]:
        if isinstance(dtype, ir.DataTypeEnum):
            return self._enum_body(dtype)
        if isinstance(dtype, (ir.DataTypeStruct, ir.DataTypeComponent)):
            return self._struct_body(dtype, ctxt)
        return None

    def _enum_body(self, dtype: ir.DataTypeEnum) -> str:
        items = getattr(dtype, "items", {}) or {}
        members = "\n".join(f"    {k} = {v}," for k, v in items.items())
        return f"typedef enum {{\n{members}\n}} {dtype.name}_t;"

    def _struct_body(
        self, dtype: ir.DataTypeStruct, ctxt: SwContext
    ) -> str:
        lines = []
        for field in getattr(dtype, "fields", []):
            ft = field.datatype
            c_field = self._map_type(ft, ctxt) or "void *"
            if isinstance(ft, ir.DataTypeArray):
                elem_c = self._resolve_elem(
                    getattr(ft, "element_type", None), ctxt
                )
                size = getattr(ft, "size", 1)
                lines.append(f"    {elem_c} {field.name}[{size}];")
            else:
                lines.append(f"    {c_field} {field.name};")
        body = "\n".join(lines)
        return f"typedef struct {{\n{body}\n}} {dtype.name}_t;"

    # ------------------------------------------------------------------
    # Topological sort
    # ------------------------------------------------------------------

    def _topological_sort(
        self, type_m: Dict[str, ir.DataType]
    ) -> List[ir.DataType]:
        """Return types in dependency order (dependencies first)."""
        visited: Set[str] = set()
        order: List[ir.DataType] = []

        def visit(dtype: ir.DataType):
            name = dtype.name
            if name in visited:
                return
            visited.add(name)
            # Visit dependencies first
            for dep in self._deps(dtype, type_m):
                visit(dep)
            order.append(dtype)

        for dtype in type_m.values():
            if dtype.name:
                visit(dtype)
        return order

    def _deps(
        self, dtype: ir.DataType, type_m: Dict[str, ir.DataType]
    ) -> List[ir.DataType]:
        deps: List[ir.DataType] = []
        if isinstance(dtype, (ir.DataTypeStruct, ir.DataTypeComponent)):
            for field in getattr(dtype, "fields", []):
                ft = field.datatype
                dep = self._resolve_ref(ft, type_m)
                if dep and dep.name and dep is not dtype:
                    deps.append(dep)
        return deps

    def _resolve_ref(
        self, dtype: ir.DataType, type_m: Dict[str, ir.DataType]
    ) -> Optional[ir.DataType]:
        if isinstance(dtype, ir.DataTypeRef):
            return type_m.get(dtype.ref_name)
        return dtype

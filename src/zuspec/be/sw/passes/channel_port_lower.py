"""ChannelPortLowerPass — lower channel fields, protocol/callable ports to SW IR.

For each component:
1. Channel fields (DataTypeChannel) → SwFifo nodes
2. Protocol port fields (FieldKind.ProtocolPort) → SwFuncPtrStruct nodes
3. Callable port fields (FieldKind.CallablePort) → single-slot SwFuncPtrStruct
4. GetIF / PutIF port fields → SwFifo with direction annotation

Function body calls:
- ``self.chan.put(v)`` / ``self.chan.push(v)`` → SwFifoPush recorded in sw_nodes
- ``self.chan.get()`` / ``self.chan.pop()`` → SwFifoPop recorded in sw_nodes
- ``self.port.method(args)`` → recorded as SwFuncPtrStruct indirect call marker
"""
from __future__ import annotations

from typing import List, Optional

from zuspec.dataclasses import ir
from zuspec.ir.core.fields import FieldKind
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.channel import (
    SwFifo,
    SwFifoPush,
    SwFifoPop,
    SwFuncSlot,
    SwFuncPtrStruct,
    SwExportBind,
)
from zuspec.be.sw.pipeline import SwPass


class ChannelPortLowerPass(SwPass):
    """Lower channel fields, protocol/callable ports, and export bindings."""

    def run(self, ctxt: SwContext) -> SwContext:
        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, ir.DataTypeComponent):
                continue
            for field in dtype.fields:
                self._lower_field(field, type_name, dtype, ctxt)
        return ctxt

    # ------------------------------------------------------------------

    def _lower_field(
        self,
        field: ir.Field,
        type_name: str,
        comp: ir.DataTypeComponent,
        ctxt: SwContext,
    ) -> None:
        dtype = self._resolve_type(field.datatype, ctxt)

        # Channel fields
        if isinstance(dtype, ir.DataTypeChannel):
            fifo = SwFifo(
                field_name=field.name,
                element_type=dtype.element_type,
                depth=getattr(dtype, "capacity", 16),
            )
            ctxt.sw_nodes.setdefault(type_name, []).append(fifo)
            return

        # Queue fields (zdc.Queue[T]) — treated as deep FIFOs
        if hasattr(ir, "QueueType") and isinstance(dtype, ir.QueueType):
            fifo = SwFifo(
                field_name=field.name,
                element_type=getattr(dtype, "element_type", None),
                depth=getattr(dtype, "depth", 16),
            )
            ctxt.sw_nodes.setdefault(type_name, []).append(fifo)
            return

        if isinstance(dtype, (ir.DataTypeGetIF, ir.DataTypePutIF)):
            fifo = SwFifo(
                field_name=field.name,
                element_type=dtype.element_type,
                depth=16,
            )
            ctxt.sw_nodes.setdefault(type_name, []).append(fifo)
            return

        # Protocol port fields
        if field.kind in (FieldKind.ProtocolPort, FieldKind.ProtocolExport):
            struct = self._lower_protocol_port(field, dtype, ctxt)
            if struct:
                ctxt.sw_nodes.setdefault(type_name, []).append(struct)
            return

        # Callable port fields
        if field.kind in (FieldKind.CallablePort, FieldKind.CallableExport):
            struct = SwFuncPtrStruct(
                struct_name=f"{field.name}_fn_t",
                slots=[SwFuncSlot(slot_name=field.name)],
            )
            ctxt.sw_nodes.setdefault(type_name, []).append(struct)
            return

        # Queue fields identified by FieldKind.QueueField
        if hasattr(FieldKind, "QueueField") and field.kind == FieldKind.QueueField:
            fifo = SwFifo(
                field_name=field.name,
                element_type=getattr(dtype, "element_type", None),
                depth=getattr(dtype, "depth", 16),
            )
            ctxt.sw_nodes.setdefault(type_name, []).append(fifo)
            return

    def _lower_protocol_port(
        self,
        field: ir.Field,
        dtype: ir.DataType,
        ctxt: SwContext,
    ) -> Optional[SwFuncPtrStruct]:
        """Build a SwFuncPtrStruct for a protocol port."""
        if isinstance(dtype, ir.DataTypeProtocol):
            slots = [
                SwFuncSlot(slot_name=method.name, signature=method)
                for method in dtype.methods
            ]
            name = dtype.name or field.name
            return SwFuncPtrStruct(
                struct_name=f"{name}_t",
                slots=slots,
                protocol_type=dtype,
            )

        if isinstance(dtype, ir.DataTypeRef):
            resolved = ctxt.type_m.get(dtype.ref_name)
            if resolved:
                return self._lower_protocol_port(field, resolved, ctxt)

        # Fallback: single-slot struct
        return SwFuncPtrStruct(
            struct_name=f"{field.name}_t",
            slots=[SwFuncSlot(slot_name=field.name)],
        )

    def _resolve_type(self, dtype: ir.DataType, ctxt: SwContext) -> ir.DataType:
        if isinstance(dtype, ir.DataTypeRef):
            resolved = ctxt.type_m.get(dtype.ref_name)
            return resolved if resolved is not None else dtype
        return dtype

"""DevirtualizePass — replace virtual port calls with direct calls.

For each ``SwFuncPtrStruct`` slot call-site, if the target implementation is
statically known (i.e., there is exactly one ``SwConnection`` binding that
export to that port slot), replace the indirect call through the function
pointer with a ``SwDirectCall`` to the concrete implementation.

When devirtualization succeeds the struct's slot call can later be
inlined by code-gen into a direct C function call, eliminating the
pointer dereference and enabling further optimisations (inlining, LTO, etc.).

This pass populates ``SwContext.direct_calls`` (currently stored per-node in
the coroutine frame lists) — for now it emits ``SwDirectCall`` IR nodes that
downstream ``CEmitPass`` can recognise.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext, SwConnection
from zuspec.be.sw.ir.channel import SwDirectCall
from zuspec.be.sw.pipeline import SwPass


class DevirtualizePass(SwPass):
    """Static devirtualization of method-port call sites.

    The pass builds a mapping ``(component, port_field_name) -> SwConnection``
    from the connections elaborated by ``ElaborateSwPass``.  It then walks
    every coroutine frame in the context looking for slot-call expressions
    and replaces them with ``SwDirectCall`` nodes when the target is unique.

    In the current implementation the frame IR does not yet expose individual
    call nodes as mutable objects, so this pass records devirtualization
    candidates in ``ctxt.devirtualized`` (a dict added by this pass) that
    ``CEmitPass`` can query at code-generation time.
    """

    def run(self, ctxt: SwContext) -> SwContext:
        # Build index: (component_name, port_name) -> connection
        port_map: Dict[Tuple[str, str], SwConnection] = {}
        for conn in ctxt.connections:
            key = (conn.initiator_component, conn.initiator_port)
            if key not in port_map:
                port_map[key] = conn
            else:
                # Multiple connections: cannot devirtualize
                port_map[key] = None  # type: ignore[assignment]

        # Record unambiguous connections
        if not hasattr(ctxt, "devirtualized"):
            ctxt.devirtualized = {}  # type: ignore[attr-defined]
        for key, conn in port_map.items():
            if conn is not None:
                ctxt.devirtualized[key] = conn  # type: ignore[attr-defined]

        return ctxt

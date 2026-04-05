"""SW backend pass infrastructure: SwPass and SwPassManager."""
from __future__ import annotations

from typing import List, Optional, Type, Any
from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext


class SwPass:
    """Base class for all SW backend passes.

    Each pass accepts a ``SwContext`` and returns a (possibly modified)
    ``SwContext``.
    """

    def run(self, ctxt: SwContext) -> SwContext:  # pragma: no cover
        raise NotImplementedError


class SwPassManager:
    """Runs a sequence of ``SwPass`` instances over a ``SwContext``.

    Usage::

        pm = SwPassManager()
        sw_ctxt = pm.run(ir_ctxt)   # ir_ctxt is a plain ir.Context
    """

    def __init__(
        self,
        passes: Optional[List[SwPass]] = None,
        output_dir: Optional[Any] = None,
        config: Optional[Any] = None,
    ):
        if passes is None:
            passes = self._build_default_pipeline(output_dir, config)
        self._passes = passes
        self.output_dir = output_dir
        self.config = config

    def _build_default_pipeline(self, output_dir, config) -> List[SwPass]:
        # Lazy imports to avoid circular dependencies at import time.
        from zuspec.be.sw.passes.elaborate import ElaborateSwPass
        from zuspec.be.sw.passes.type_lower import TypeLowerPass
        from zuspec.be.sw.passes.activity_lower import ActivityLowerPass
        from zuspec.be.sw.passes.resource_lower import ResourceLowerPass
        from zuspec.be.sw.passes.channel_port_lower import ChannelPortLowerPass
        from zuspec.be.sw.passes.async_lower import AsyncLowerPass
        from zuspec.be.sw.passes.c_emit import CEmitPass
        return [
            ElaborateSwPass(),
            TypeLowerPass(),
            ActivityLowerPass(),
            ResourceLowerPass(),
            ChannelPortLowerPass(),
            AsyncLowerPass(),
            CEmitPass(),
        ]

    def run(self, ctxt: ir.Context, py_globals: Optional[dict] = None) -> SwContext:
        """Wrap *ctxt* in a ``SwContext`` and run all registered passes."""
        if isinstance(ctxt, SwContext):
            sw_ctxt = ctxt
        else:
            sw_ctxt = SwContext(type_m=dict(ctxt.type_m))
        if py_globals is not None:
            sw_ctxt.py_globals = py_globals

        for p in self._passes:
            sw_ctxt = p.run(sw_ctxt)

        return sw_ctxt

    def verify_ready(self, ctxt: SwContext) -> None:
        """Raise ``RuntimeError`` if *ctxt* contains any unlowered ``DomainNode``s.

        A node is considered "unlowered" if it is a ``DomainNode`` subclass
        that is *not* one of the recognised SW IR node types (i.e. the pass
        pipeline has not handled it).
        """
        from zuspec.be.sw.ir.base import SwNode

        for type_name, nodes in ctxt.sw_nodes.items():
            for node in nodes:
                if not isinstance(node, SwNode):
                    raise RuntimeError(
                        f"Unlowered node {type(node).__name__} in component "
                        f"'{type_name}' — ensure all required passes have run."
                    )

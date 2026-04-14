"""BulkSyncSchedulerPass — emit bulk-synchronisation scheduling code.

In Loosely-Timed (LT) TLM mode, initiators accumulate local time using
``ZSP_WAIT_PS`` and only synchronise with the global timebase at quantum
boundaries.  This pass generates the C glue that wires components together
via a bulk-sync scheduler so that:

1. Each initiator thread advances independently until it reaches its LT
   quantum boundary.
2. At the quantum boundary a ``zsp_timebase_wait_ps()`` call is issued,
   yielding back to the scheduler.
3. The scheduler advances the global time to the minimum of all pending
   quantum expiry times and re-activates the appropriate threads.

Current status: stub that records scheduling metadata into ``ctxt`` for
consumption by ``CEmitPass``.  Full C code generation for the scheduler
loop is deferred to a later phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.pipeline import SwPass


@dataclass
class BulkSyncEntry:
    """Describes a single component thread participating in bulk-sync."""
    component_name: str
    run_method: str          # name of the component's top-level run/execute function
    quantum_ps: int          # LT quantum in picoseconds


class BulkSyncSchedulerPass(SwPass):
    """Record bulk-synchronisation scheduling metadata.

    For every ``DataTypeComponent`` that has an async ``run`` (or ``execute``)
    method with ``has_wait=True`` (from ``WaitPointAnalysisPass``), this pass
    records a ``BulkSyncEntry`` in ``ctxt.bulk_sync_entries``.

    A later code-generation step in ``CEmitPass`` (or a dedicated emitter)
    will use these entries to generate the scheduler loop.
    """

    def __init__(self, lt_quantum_ps: int = 1_000_000):
        self._lt_quantum_ps = lt_quantum_ps

    def run(self, ctxt: SwContext) -> SwContext:
        if not hasattr(ctxt, "bulk_sync_entries"):
            ctxt.bulk_sync_entries: List[BulkSyncEntry] = []  # type: ignore[attr-defined]

        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, ir.DataTypeComponent):
                continue
            # Look for a run / execute / main method
            for fn in dtype.functions:
                if fn.name not in ("run", "execute", "body", "main"):
                    continue
                if not fn.is_async:
                    continue
                lat = ctxt.method_latencies.get((type_name, fn.name))
                if lat is not None and lat.has_wait:
                    ctxt.bulk_sync_entries.append(  # type: ignore[attr-defined]
                        BulkSyncEntry(
                            component_name=type_name,
                            run_method=fn.name,
                            quantum_ps=self._lt_quantum_ps,
                        )
                    )
                    break  # Only register each component once

        return ctxt

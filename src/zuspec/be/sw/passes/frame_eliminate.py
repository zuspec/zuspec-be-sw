"""FrameEliminatePass — remove unnecessary coroutine frames.

A coroutine frame (``SwCoroutineFrame``) is the heap-allocated state block
used to suspend and resume a coroutine at each ``await`` point.  When static
analysis can prove that a coroutine never suspends (i.e., it has zero
``await`` points on any execution path), the frame can be eliminated: the
function becomes a plain C function returning ``void`` instead of a task
coroutine.

This pass is a pre-condition for ``BulkSyncSchedulerPass`` and also enables
``DevirtualizePass`` to emit simpler direct calls.

Current status: stub that marks zero-wait methods as frame-eliminable by
recording them in ``ctxt.frame_eliminable`` (a set of ``(component, method)``
keys).  Actual frame elimination (rewriting the emitted C code) is left for
a later implementation phase.
"""
from __future__ import annotations

from typing import Set, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext, MethodLatency
from zuspec.be.sw.pipeline import SwPass


class FrameEliminatePass(SwPass):
    """Mark async methods that never wait as frame-eliminable.

    Reads ``SwContext.method_latencies`` (populated by ``WaitPointAnalysisPass``)
    and records any method whose ``has_wait`` is ``False`` into the set
    ``ctxt.frame_eliminable``.

    ``CEmitPass`` can later query this set to emit a plain C function instead
    of a coroutine for those methods.
    """

    def run(self, ctxt: SwContext) -> SwContext:
        if not hasattr(ctxt, "frame_eliminable"):
            ctxt.frame_eliminable: Set[Tuple[str, str]] = set()  # type: ignore[attr-defined]

        for key, lat in ctxt.method_latencies.items():
            if not lat.has_wait:
                ctxt.frame_eliminable.add(key)  # type: ignore[attr-defined]

        return ctxt

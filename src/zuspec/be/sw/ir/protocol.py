"""EvalProtocol — execution protocol for Zuspec components."""
from __future__ import annotations

import enum


class EvalProtocol(enum.Enum):
    """Execution protocol inferred by ComponentClassifyPass."""
    RTL          = "rtl"           # only @sync / @comb; deferred writes
    ALGORITHMIC  = "algorithmic"   # only await / wait_*; no _nxt shadows
    CYCLE_APPROX = "cycle_approx"  # wait_cycles only; no bit-level signals
    MLS          = "mls"           # mixed: RTL subregions + behavioral

"""SW IR nodes for inference patterns: buffer, stream, and schedule.

These nodes are produced by an inference-lowering pass and consumed
by CEmitPass to generate static tables and solve functions.
"""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Tuple

from .base import SwNode


@dc.dataclass(kw_only=True)
class SwBufferSolveFunc(SwNode):
    """Generated solve function for a buffer producer/consumer pair.

    The code generator emits a C function that:
    - Solves the producer with back-propagated consumer constraints
    - Passes concrete values from producer to consumer via a param struct
    """
    producer_type: str = ""
    consumer_type: str = ""
    shared_fields: List[str] = dc.field(default_factory=list)
    backprop_constraints: List[Dict[str, object]] = dc.field(default_factory=list)
    n_producers: int = 1


@dc.dataclass(kw_only=True)
class SwStreamJointSolveFunc(SwNode):
    """Generated joint solve function for a stream-linked pair.

    The code generator emits a single C function that contains variables
    from both producer and consumer, with shared fields unified.
    """
    producer_type: str = ""
    consumer_type: str = ""
    shared_fields: List[str] = dc.field(default_factory=list)
    producer_private_fields: List[str] = dc.field(default_factory=list)
    consumer_private_fields: List[str] = dc.field(default_factory=list)


@dc.dataclass(kw_only=True)
class SwScheduleStageTable(SwNode):
    """Static stage table for a schedule block.

    Emitted as a ROM-resident const array that the runtime dispatcher
    iterates over: spawn all units per stage, join, advance.
    """
    schedule_name: str = ""
    n_stages: int = 0
    n_actions: int = 0
    stages: List[List[List[int]]] = dc.field(default_factory=list)
    # stages[level][unit_idx] = [action_ids...]

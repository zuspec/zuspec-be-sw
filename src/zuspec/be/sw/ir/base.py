"""SW IR base types: SwNode and SwContext."""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Set, Any, Tuple, TYPE_CHECKING

from zuspec.ir.core.domain_node import DomainNode
from zuspec.ir.core.connection import Connection
from zuspec.dataclasses import ir
from zuspec.be.sw.ir.protocol import EvalProtocol


@dc.dataclass(kw_only=True)
class SwNode(DomainNode):
    """Abstract base class for all SW IR nodes.

    All SW IR nodes extend this class, which in turn extends DomainNode.
    The ``inputs``/``outputs`` methods return empty lists by default; subclasses
    override them where connections are meaningful.
    """

    def inputs(self) -> List[Connection]:
        return []

    def outputs(self) -> List[Connection]:
        return []


@dc.dataclass(kw_only=True)
class SwConnection:
    """A resolved port-to-export binding derived from a ``__bind__`` declaration.

    Attributes
    ----------
    initiator_component:
        Type name of the component owning the initiating (port) side.
    initiator_port:
        Field name of the port on the initiator component.
    initiator_inst_path:
        Dot-separated instance path of the initiator component instance.
    target_component:
        Type name of the component owning the export side.
    target_export:
        Field name of the export on the target component.
    target_inst_path:
        Dot-separated instance path of the target component instance.
    protocol:
        The ``ir.DataTypeProtocol`` node shared by the port and export.
    """
    initiator_component: str = dc.field(default="")
    initiator_port: str = dc.field(default="")
    initiator_inst_path: str = dc.field(default="")
    target_component: str = dc.field(default="")
    target_export: str = dc.field(default="")
    target_inst_path: str = dc.field(default="")
    protocol: Optional[Any] = dc.field(default=None)  # ir.DataTypeProtocol


@dc.dataclass
class MethodLatency:
    """Static latency bounds for a single component method.

    Attributes
    ----------
    min_ps:
        Minimum accumulated wait time across all execution paths (ps).
        Zero if no ``wait()`` on the shortest path.
    max_ps:
        Maximum accumulated wait time.  ``sys.maxsize`` when unbounded
        (e.g. the method contains an infinite loop with a wait inside).
    has_wait:
        True if the method calls ``wait()`` directly or transitively.
    """
    min_ps: int = 0
    max_ps: int = 0
    has_wait: bool = False


@dc.dataclass
class SwContext(ir.Context):
    """Extended IR context used by all SW backend passes.

    Attributes
    ----------
    root_inst:
        The top-level ``SwCompInst`` produced by ``ElaborateSwPass``.
    inst_m:
        Mapping from dot-separated instance path to ``SwCompInst``.
    sw_nodes:
        Mapping from owning type name to the list of ``SwNode``s attached to
        that type (e.g. schedulers, coroutine frames, fifo declarations).
    c_type_m:
        Mapping from ``DataType.name`` to its canonical C type string.
    c_type_bodies:
        Mapping from ``DataType.name`` to the C struct/enum body definition
        string.  Only populated for aggregate types.
    output_files:
        List of paths (``str`` or ``pathlib.Path``) of files written by
        ``CEmitPass``.
    connections:
        Resolved port-to-export bindings populated by ``ElaboratePass`` from
        ``__bind__`` declarations.
    method_latencies:
        Static latency bounds populated by ``WaitPointAnalysisPass``.
        Key is ``(component_name, method_name)``.
    """

    root_inst: Optional[Any] = dc.field(default=None)
    inst_m: Dict[str, Any] = dc.field(default_factory=dict)
    sw_nodes: Dict[str, List[SwNode]] = dc.field(default_factory=dict)
    c_type_m: Dict[str, str] = dc.field(default_factory=dict)
    c_type_bodies: Dict[str, str] = dc.field(default_factory=dict)
    output_files: List[Any] = dc.field(default_factory=list)
    py_globals: Dict[str, Any] = dc.field(default_factory=dict)
    """Python module globals from which the component was built.

    Populated by ``SwPassManager`` with the module globals of the root
    component class.  Used by ``StmtGenerator`` to resolve Python enum
    references (e.g. ``AluOp.ADD`` → integer value) in generated C.
    """

    # ------------------------------------------------------------------
    # TLM / method-port annotations
    # ------------------------------------------------------------------
    connections: List[SwConnection] = dc.field(default_factory=list)
    """Resolved port-to-export bindings from ``__bind__`` elaboration."""
    method_latencies: Dict[Tuple[str, str], MethodLatency] = dc.field(default_factory=dict)
    """Static latency bounds per (component_name, method_name)."""
    tlm_sync_mode: str = dc.field(default="")
    """TLM synchronisation mode: ``"lt"`` (loosely-timed) or ``"precise"`` (or empty for
    non-TLM generation).  Set by ``generate_tlm()``; controls whether coroutine wait
    points emit ``ZSP_WAIT_PS`` (TLM) or the legacy ``zsp_timebase_wait`` call."""
    tlm_lt_quantum_ps: int = dc.field(default=1_000_000)
    """LT quantum in picoseconds.  Used by ``BulkSyncSchedulerPass`` and ``FrameEliminatePass``
    to determine which methods can skip the coroutine frame.  Default: 1 µs."""

    # ------------------------------------------------------------------
    # RTL-specific annotations (populated by passes/rtl/ pipeline)
    # ------------------------------------------------------------------
    rtl_component: Optional[Any] = dc.field(default=None)
    """The DataTypeComponent being processed by the RTL sub-pipeline."""
    rtl_component_class: Optional[Any] = dc.field(default=None)
    """The original Python class passed to generate() / compile_and_load()."""
    rtl_protocol: Optional[EvalProtocol] = dc.field(default=None)
    """Execution protocol determined by ComponentClassifyPass."""
    rtl_tier: int = dc.field(default=0)
    """RTL tier (0=pure sync/comb, 1=pipeline, 2=behavioral)."""
    rtl_domain_period_ps: int = dc.field(default=10_000)
    """Primary clock period in picoseconds."""
    rtl_nxt_fields: Set[str] = dc.field(default_factory=set)
    """Fields written in @sync bodies; require _nxt shadow copies."""
    rtl_comb_order: List[Any] = dc.field(default_factory=list)
    """Topologically-sorted @comb functions for combinational logic."""
    rtl_pipeline_clock_body: List[str] = dc.field(default_factory=list)
    """Generated C lines for the pipeline clock-edge function."""
    rtl_behav_processes: List[Any] = dc.field(default_factory=list)
    """Behavioral (@process) coroutine descriptors."""
    rtl_suspension_points: List[dict] = dc.field(default_factory=list)
    """Populated by RtlCEmitPass when debug=True: suspension-point dicts."""
    rtl_debug: bool = dc.field(default=False)
    """When True, emit #line directives, debug info, and GDB script."""
    rtl_warnings: List[str] = dc.field(default_factory=list)
    """Warnings accumulated during the RTL pass pipeline."""

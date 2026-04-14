"""SW IR base types: SwNode and SwContext."""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Set, Any, TYPE_CHECKING

from zuspec.dataclasses.ir.domain_node import DomainNode
from zuspec.dataclasses.ir.connection import Connection
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

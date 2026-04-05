"""SW IR base types: SwNode and SwContext."""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from zuspec.dataclasses.ir.domain_node import DomainNode
from zuspec.dataclasses.ir.connection import Connection
from zuspec.dataclasses import ir


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

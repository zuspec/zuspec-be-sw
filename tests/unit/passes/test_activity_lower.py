"""Tests for ActivityLowerPass."""
import sys
from pathlib import Path

import zuspec.dataclasses as zdc

from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.activity import (
    SwSchedulerNode, SwActionExec, SwSeqBlock, SwParBlock, SwSelectNode, SwSelectBranch,
)
from zuspec.be.sw.passes.activity_lower import (
    ActivityLowerPass,
    _SwRepeat, _SwDoWhile, _SwWhileDo, _SwForeach, _SwReplicate, _SwIfElse, _SwMatch,
)


def _build_and_lower(py_cls):
    ctxt = zdc.DataModelFactory().build(py_cls)
    sw_ctxt = SwContext(type_m=dict(ctxt.type_m))
    return ActivityLowerPass().run(sw_ctxt)


def _sched(sw_ctxt, cls_name=None):
    """Return the first SwSchedulerNode in sw_nodes."""
    for k, nodes in sw_ctxt.sw_nodes.items():
        if cls_name is None or cls_name in k:
            for n in nodes:
                if isinstance(n, SwSchedulerNode):
                    return n
    return None


# --- Fixtures defined inline (no activity, so safe to define here) ---

@zdc.dataclass
class InlineLeaf(zdc.Action):
    pass


# --- Tests using file-level fixtures ---

def test_no_activity_produces_no_sched():
    sw_ctxt = _build_and_lower(InlineLeaf)
    assert _sched(sw_ctxt) is None


def test_sequence_block():
    from fixtures.activity_components import SeqParent
    sw_ctxt = _build_and_lower(SeqParent)
    sched = _sched(sw_ctxt, "SeqParent")
    assert sched is not None
    assert isinstance(sched, SwSchedulerNode)
    root = sched.root
    assert isinstance(root, SwSeqBlock)
    assert len(root.children) == 2
    for child in root.children:
        assert isinstance(child, SwActionExec)
    assert root.children[0].handle_name == "a"
    assert root.children[1].handle_name == "b"


def test_parallel_block():
    from fixtures.activity_components import ParParent
    sw_ctxt = _build_and_lower(ParParent)
    sched = _sched(sw_ctxt, "ParParent")
    assert sched is not None
    root = sched.root
    # Root is a SwSeqBlock wrapping the parallel block
    par = root.children[0] if isinstance(root, SwSeqBlock) else root
    assert isinstance(par, SwParBlock)
    assert par.join == "all"
    assert len(par.children) == 2


def test_select_node():
    from fixtures.activity_components import SelectParent
    sw_ctxt = _build_and_lower(SelectParent)
    sched = _sched(sw_ctxt, "SelectParent")
    assert sched is not None
    root = sched.root
    sel = root.children[0] if isinstance(root, SwSeqBlock) else root
    assert isinstance(sel, SwSelectNode)
    assert len(sel.branches) == 2
    for branch in sel.branches:
        assert isinstance(branch, SwSelectBranch)
        assert branch.body is not None


def test_scheduler_node_has_action_type():
    from fixtures.activity_components import SeqParent
    sw_ctxt = _build_and_lower(SeqParent)
    sched = _sched(sw_ctxt, "SeqParent")
    assert sched.action_type is not None

"""Tests for SW IR activity nodes."""
from zuspec.ir.core.domain_node import DomainNode
from zuspec.be.sw.ir.base import SwNode
from zuspec.be.sw.ir.activity import (
    SwSchedulerNode,
    SwActionExec,
    SwSeqBlock,
    SwParBlock,
    SwSelectBranch,
    SwSelectNode,
)


def test_sw_scheduler_node_instantiation():
    node = SwSchedulerNode()
    assert isinstance(node, SwNode)
    assert isinstance(node, DomainNode)
    assert node.action_type is None
    assert node.root is None


def test_sw_action_exec_instantiation():
    node = SwActionExec()
    assert isinstance(node, SwNode)
    assert node.action_type is None
    assert node.handle_name is None
    assert node.solve_constraints == []


def test_sw_seq_block_instantiation():
    node = SwSeqBlock()
    assert isinstance(node, SwNode)
    assert node.children == []


def test_sw_seq_block_with_children():
    a = SwActionExec(handle_name="a")
    b = SwActionExec(handle_name="b")
    seq = SwSeqBlock(children=[a, b])
    assert len(seq.children) == 2
    assert seq.children[0].handle_name == "a"


def test_sw_par_block_default_join():
    node = SwParBlock()
    assert isinstance(node, SwNode)
    assert node.join == "all"
    assert node.children == []


def test_sw_par_block_join_variants():
    for join in ("all", "first", "none", "select"):
        node = SwParBlock(join=join)
        assert node.join == join


def test_sw_select_branch_instantiation():
    branch = SwSelectBranch()
    assert isinstance(branch, SwNode)
    assert branch.weight is None
    assert branch.guard is None
    assert branch.body is None


def test_sw_select_node_instantiation():
    node = SwSelectNode()
    assert isinstance(node, SwNode)
    assert node.branches == []


def test_sw_select_node_with_branches():
    b1 = SwSelectBranch(body=SwSeqBlock())
    b2 = SwSelectBranch(body=SwSeqBlock())
    sel = SwSelectNode(branches=[b1, b2])
    assert len(sel.branches) == 2


def test_all_activity_nodes_repr_do_not_crash():
    nodes = [
        SwSchedulerNode(),
        SwActionExec(),
        SwSeqBlock(),
        SwParBlock(),
        SwSelectBranch(),
        SwSelectNode(),
    ]
    for node in nodes:
        r = repr(node)
        assert type(node).__name__ in r

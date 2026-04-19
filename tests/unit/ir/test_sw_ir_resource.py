"""Tests for SW IR resource nodes."""
from zuspec.ir.core.domain_node import DomainNode
from zuspec.be.sw.ir.base import SwNode
from zuspec.be.sw.ir.resource import SwMutexAcquire, SwMutexRelease, SwIndexedSelect


def test_sw_mutex_acquire_instantiation():
    node = SwMutexAcquire()
    assert isinstance(node, SwNode)
    assert isinstance(node, DomainNode)
    assert node.pool_expr is None
    assert node.out_var is None
    assert node.body is None


def test_sw_mutex_release_instantiation():
    node = SwMutexRelease()
    assert isinstance(node, SwNode)
    assert node.pool_expr is None
    assert node.acquire_ref is None


def test_sw_mutex_acquire_release_linked():
    acq = SwMutexAcquire(out_var="unit")
    rel = SwMutexRelease(acquire_ref=acq)
    assert rel.acquire_ref is acq
    assert acq.out_var == "unit"


def test_sw_indexed_select_instantiation():
    node = SwIndexedSelect()
    assert isinstance(node, SwNode)
    assert node.pool_expr is None
    assert node.index_var is None


def test_all_resource_nodes_repr_do_not_crash():
    for node in [SwMutexAcquire(), SwMutexRelease(), SwIndexedSelect()]:
        r = repr(node)
        assert type(node).__name__ in r

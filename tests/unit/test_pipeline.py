"""Integration tests for the full SwPassManager pipeline (Phase 8).

Runs the complete pipeline on all fixture components and verifies:
1. Returns a SwContext with no unlowered DomainNodes.
2. Produces at least one .h and one .c file.
3. All produced files have the correct extension and non-empty content.
"""
import sys
import pytest
import zuspec.dataclasses as zdc

from zuspec.be.sw.pipeline import SwPassManager
from zuspec.be.sw.ir.base import SwContext, SwNode


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

def _build(py_cls):
    return zdc.DataModelFactory().build(py_cls)


def _run_pipeline(py_cls):
    ctxt = _build(py_cls)
    pm = SwPassManager()
    return pm, pm.run(ctxt)


# ---------------------------------------------------------------------------
# Simple component
# ---------------------------------------------------------------------------

def test_simple_comp_pipeline_runs():
    from fixtures.simple_components import SimpleComp
    pm, sw_ctxt = _run_pipeline(SimpleComp)
    assert isinstance(sw_ctxt, SwContext)


def test_simple_comp_produces_h_and_c():
    from fixtures.simple_components import SimpleComp
    _, sw_ctxt = _run_pipeline(SimpleComp)
    names = [n for n, _ in sw_ctxt.output_files]
    assert any(n.endswith(".h") for n in names), f"No .h files in {names}"
    assert any(n.endswith(".c") for n in names), f"No .c files in {names}"


def test_simple_comp_output_non_empty():
    from fixtures.simple_components import SimpleComp
    _, sw_ctxt = _run_pipeline(SimpleComp)
    for fname, content in sw_ctxt.output_files:
        assert content.strip(), f"Empty output file: {fname}"


def test_simple_comp_verify_ready():
    from fixtures.simple_components import SimpleComp
    pm, sw_ctxt = _run_pipeline(SimpleComp)
    pm.verify_ready(sw_ctxt)  # must not raise


# ---------------------------------------------------------------------------
# Method component
# ---------------------------------------------------------------------------

def test_method_comp_pipeline_runs():
    from fixtures.method_components import ComponentWithMethod
    pm, sw_ctxt = _run_pipeline(ComponentWithMethod)
    assert isinstance(sw_ctxt, SwContext)


def test_method_comp_verify_ready():
    from fixtures.method_components import ComponentWithMethod
    pm, sw_ctxt = _run_pipeline(ComponentWithMethod)
    pm.verify_ready(sw_ctxt)


# ---------------------------------------------------------------------------
# Activity components (seq/par/select)
# ---------------------------------------------------------------------------

def test_seq_parent_pipeline_runs():
    from fixtures.activity_components import SeqParent
    pm, sw_ctxt = _run_pipeline(SeqParent)
    pm.verify_ready(sw_ctxt)


def test_par_parent_pipeline_runs():
    from fixtures.activity_components import ParParent
    pm, sw_ctxt = _run_pipeline(ParParent)
    pm.verify_ready(sw_ctxt)


def test_select_parent_pipeline_runs():
    from fixtures.activity_components import SelectParent
    pm, sw_ctxt = _run_pipeline(SelectParent)
    pm.verify_ready(sw_ctxt)


# ---------------------------------------------------------------------------
# Channel (Producer / Consumer)
# ---------------------------------------------------------------------------

def test_producer_pipeline_runs():
    from fixtures.channel_components import Producer
    pm, sw_ctxt = _run_pipeline(Producer)
    pm.verify_ready(sw_ctxt)


def test_consumer_pipeline_runs():
    from fixtures.channel_components import Consumer
    pm, sw_ctxt = _run_pipeline(Consumer)
    pm.verify_ready(sw_ctxt)


# ---------------------------------------------------------------------------
# Resource (PoolComp)
# ---------------------------------------------------------------------------

def test_pool_comp_pipeline_runs():
    from fixtures.resource_components import PoolComp
    pm, sw_ctxt = _run_pipeline(PoolComp)
    pm.verify_ready(sw_ctxt)


# ---------------------------------------------------------------------------
# CGenerator delegation tests
# ---------------------------------------------------------------------------

def test_c_generator_use_pass_pipeline(tmp_path):
    from fixtures.simple_components import SimpleComp
    from zuspec.be.sw.c_generator import CGenerator
    ctxt = _build(SimpleComp)
    gen = CGenerator(output_dir=tmp_path, use_pass_pipeline=True)
    files = gen.generate(ctxt)
    assert len(files) > 0, "Expected generated files"
    assert any(str(f).endswith(".h") for f in files)
    assert any(str(f).endswith(".c") for f in files)


def test_c_generator_pass_pipeline_files_written(tmp_path):
    from fixtures.simple_components import SimpleComp
    from zuspec.be.sw.c_generator import CGenerator
    ctxt = _build(SimpleComp)
    gen = CGenerator(output_dir=tmp_path, use_pass_pipeline=True)
    files = gen.generate(ctxt)
    for f in files:
        assert f.exists(), f"File not written to disk: {f}"


def test_c_generator_old_path_still_works(tmp_path):
    """Default (use_pass_pipeline=False) code path must not break."""
    from fixtures.simple_components import SimpleComp
    from zuspec.be.sw.c_generator import CGenerator
    ctxt = _build(SimpleComp)
    gen = CGenerator(output_dir=tmp_path, use_pass_pipeline=False)
    files = gen.generate(ctxt)
    # Existing path returns a list (may be empty if component is trivial)
    assert isinstance(files, list)


# ---------------------------------------------------------------------------
# verify_ready — negative test
# ---------------------------------------------------------------------------

def test_verify_ready_raises_on_unlowered_node():
    """verify_ready must raise when a non-SwNode appears in sw_nodes."""
    from zuspec.dataclasses.ir.domain_node import DomainNode

    class RogueNode(DomainNode):
        def inputs(self):
            return []
        def outputs(self):
            return []

    sw_ctxt = SwContext(type_m={})
    sw_ctxt.sw_nodes["Comp"] = [RogueNode()]
    pm = SwPassManager()
    with pytest.raises(RuntimeError, match="Unlowered"):
        pm.verify_ready(sw_ctxt)

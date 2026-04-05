"""Tests for MemRegAccessLowerPass (Phase 9)."""
from __future__ import annotations

import dataclasses as dc
from typing import List

import pytest

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.memory import SwRegRead, SwRegWrite, SwMemRead, SwMemWrite
from zuspec.be.sw.passes.mem_reg_lower import MemRegAccessLowerPass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args() -> ir.Arguments:
    return ir.Arguments(
        posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
    )


def _make_reg_type(name: str = "MyReg", bits: int = 32) -> ir.DataTypeRegister:
    return ir.DataTypeRegister(
        name=name,
        super=None,
        fields=[],
        functions=[],
        register_value_type=ir.DataTypeInt(bits=bits, signed=False),
        size_bits=bits,
    )


def _make_comp(name: str, functions: list) -> ir.DataTypeComponent:
    return ir.DataTypeComponent(name=name, super=None, fields=[], functions=functions)


def _reg_call(method: str, recv_name: str = "reg", args=None) -> ir.ExprCall:
    return ir.ExprCall(
        func=ir.ExprAttribute(
            value=ir.ExprAttribute(
                value=ir.TypeExprRefSelf(), attr=recv_name
            ),
            attr=method,
        ),
        args=args or [],
    )


def _mem_call(method: str, addr_val: int = 0x1000, data_val: int = None) -> ir.ExprCall:
    args = [ir.ExprConstant(value=addr_val)]
    if data_val is not None:
        args.append(ir.ExprConstant(value=data_val))
    return ir.ExprCall(
        func=ir.ExprAttribute(
            value=ir.ExprAttribute(
                value=ir.TypeExprRefSelf(), attr="mem"
            ),
            attr=method,
        ),
        args=args,
    )


def _func_with(name: str, *calls: ir.ExprCall) -> ir.Function:
    return ir.Function(
        name=name,
        args=_make_args(),
        body=[ir.StmtExpr(expr=c) for c in calls],
        is_async=False,
    )


def _run(comp: ir.DataTypeComponent, extra_types=None, mode="iss"):
    type_m = {comp.name: comp}
    if extra_types:
        type_m.update(extra_types)
    sw_ctxt = SwContext(type_m=type_m)
    MemRegAccessLowerPass(mode=mode).run(sw_ctxt)
    return sw_ctxt


# ---------------------------------------------------------------------------
# Register read tests
# ---------------------------------------------------------------------------

def test_register_read_iss_mode():
    func = _func_with("run", _reg_call("read"))
    comp = _make_comp("RegUser", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("RegUser", [])
    reads = [n for n in nodes if isinstance(n, SwRegRead)]
    assert len(reads) == 1
    assert reads[0].mode == "iss"


def test_register_read_val_iss_mode():
    func = _func_with("run", _reg_call("read_val"))
    comp = _make_comp("RegUser2", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("RegUser2", [])
    reads = [n for n in nodes if isinstance(n, SwRegRead)]
    assert len(reads) == 1


def test_register_write_iss_mode():
    func = _func_with("run", _reg_call("write", args=[ir.ExprConstant(value=0xFF)]))
    comp = _make_comp("RegWriter", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("RegWriter", [])
    writes = [n for n in nodes if isinstance(n, SwRegWrite)]
    assert len(writes) == 1
    assert writes[0].mode == "iss"


def test_register_write_val_iss_mode():
    func = _func_with("run", _reg_call("write_val", args=[ir.ExprConstant(value=42)]))
    comp = _make_comp("RegWriter2", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("RegWriter2", [])
    writes = [n for n in nodes if isinstance(n, SwRegWrite)]
    assert len(writes) == 1


def test_register_read_bfm_mode():
    func = _func_with("run", _reg_call("read"))
    comp = _make_comp("BFMUser", [func])
    sw_ctxt = _run(comp, mode="bfm")
    nodes = sw_ctxt.sw_nodes.get("BFMUser", [])
    reads = [n for n in nodes if isinstance(n, SwRegRead)]
    assert len(reads) == 1
    assert reads[0].mode == "bfm"


# ---------------------------------------------------------------------------
# Memory read/write tests
# ---------------------------------------------------------------------------

def test_memory_read_32():
    func = _func_with("fetch", _mem_call("read32"))
    comp = _make_comp("MemUser", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("MemUser", [])
    reads = [n for n in nodes if isinstance(n, SwMemRead)]
    assert len(reads) == 1
    assert reads[0].width == 32


def test_memory_write_8():
    func = _func_with("store", _mem_call("write8", data_val=0xAB))
    comp = _make_comp("Writer8", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("Writer8", [])
    writes = [n for n in nodes if isinstance(n, SwMemWrite)]
    assert len(writes) == 1
    assert writes[0].width == 8


def test_memory_write_16():
    func = _func_with("store", _mem_call("write16", data_val=0x1234))
    comp = _make_comp("Writer16", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("Writer16", [])
    writes = [n for n in nodes if isinstance(n, SwMemWrite)]
    assert writes[0].width == 16


def test_memory_write_64():
    func = _func_with("store", _mem_call("write64", data_val=0xDEAD))
    comp = _make_comp("Writer64", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("Writer64", [])
    writes = [n for n in nodes if isinstance(n, SwMemWrite)]
    assert writes[0].width == 64


def test_signed_memory_read_default_unsigned():
    func = _func_with("fetch", _mem_call("read32"))
    comp = _make_comp("SignedUser", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("SignedUser", [])
    reads = [n for n in nodes if isinstance(n, SwMemRead)]
    assert reads[0].signed is False


# ---------------------------------------------------------------------------
# Invalid mode
# ---------------------------------------------------------------------------

def test_invalid_mode_raises():
    with pytest.raises(ValueError, match="Unknown mode"):
        MemRegAccessLowerPass(mode="rtl")


# ---------------------------------------------------------------------------
# No false positives on unrelated methods
# ---------------------------------------------------------------------------

def test_unrelated_method_not_lowered():
    func = _func_with("run", ir.ExprCall(
        func=ir.ExprAttribute(
            value=ir.TypeExprRefSelf(), attr="do_something"
        ),
        args=[],
    ))
    comp = _make_comp("Clean", [func])
    sw_ctxt = _run(comp)
    nodes = sw_ctxt.sw_nodes.get("Clean", [])
    assert all(
        not isinstance(n, (SwRegRead, SwRegWrite, SwMemRead, SwMemWrite))
        for n in nodes
    )

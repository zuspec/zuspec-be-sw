"""Tests for TypeLowerPass."""
import dataclasses as dc
from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.passes.type_lower import TypeLowerPass


def _run(*dtypes) -> SwContext:
    ctxt = SwContext()
    for dtype in dtypes:
        if dtype.name:
            ctxt.type_m[dtype.name] = dtype
    return TypeLowerPass().run(ctxt)


# -- Integer types --

def test_int_types():
    mapping = {
        (8, True): "int8_t",
        (8, False): "uint8_t",
        (16, True): "int16_t",
        (16, False): "uint16_t",
        (32, True): "int32_t",
        (32, False): "uint32_t",
        (64, True): "int64_t",
        (64, False): "uint64_t",
    }
    for (bits, signed), expected in mapping.items():
        dtype = ir.DataTypeInt(name=f"int_{bits}_{signed}", bits=bits, signed=signed)
        ctxt = _run(dtype)
        assert ctxt.c_type_m[dtype.name] == expected, f"bits={bits} signed={signed}"


def test_uptr():
    dtype = ir.DataTypeUptr(name="uptr_t")
    ctxt = _run(dtype)
    assert ctxt.c_type_m["uptr_t"] == "uintptr_t"


def test_chandle():
    dtype = ir.DataTypeChandle(name="chandle_t")
    ctxt = _run(dtype)
    assert ctxt.c_type_m["chandle_t"] == "void *"


def test_string():
    dtype = ir.DataTypeString(name="str_t")
    ctxt = _run(dtype)
    assert ctxt.c_type_m["str_t"] == "const char *"


# -- Enum --

def test_enum():
    dtype = ir.DataTypeEnum(name="Color", items={"RED": 0, "GREEN": 1, "BLUE": 2})
    ctxt = _run(dtype)
    assert ctxt.c_type_m["Color"] == "Color_t"
    body = ctxt.c_type_bodies["Color"]
    assert "RED = 0" in body
    assert "GREEN = 1" in body
    assert "BLUE = 2" in body
    assert "typedef enum" in body
    assert "Color_t" in body


# -- Struct --

def test_struct():
    field_a = ir.Field(name="a", datatype=ir.DataTypeInt(bits=32, signed=False))
    field_b = ir.Field(name="b", datatype=ir.DataTypeInt(bits=8, signed=True))
    dtype = ir.DataTypeStruct(name="Point", super=None, fields=[field_a, field_b])
    ctxt = _run(dtype)
    assert ctxt.c_type_m["Point"] == "Point_t"
    body = ctxt.c_type_bodies["Point"]
    assert "uint32_t a" in body
    assert "int8_t b" in body
    assert "typedef struct" in body


# -- Channel / list --

def test_channel_type():
    dtype = ir.DataTypeChannel(name="MyChan", element_type=ir.DataTypeInt(bits=32, signed=False))
    ctxt = _run(dtype)
    assert ctxt.c_type_m["MyChan"] == "zsp_fifo_t"


def test_list_unknown_size():
    dtype = ir.DataTypeList(name="IntList", element_type=ir.DataTypeInt(bits=32, signed=False))
    ctxt = _run(dtype)
    assert ctxt.c_type_m["IntList"] == "zsp_list_t"


# -- Address space / addr handle --

def test_address_space():
    dtype = ir.DataTypeAddressSpace(name="MyAS")
    ctxt = _run(dtype)
    assert ctxt.c_type_m["MyAS"] == "zsp_addr_space_t *"


def test_addr_handle():
    dtype = ir.DataTypeAddrHandle(name="MyHandle")
    ctxt = _run(dtype)
    assert ctxt.c_type_m["MyHandle"] == "uintptr_t"


# -- Topological order --

def test_topological_order():
    """Struct B referenced by struct A must appear before A in emitted bodies."""
    field_b_inner = ir.Field(name="val", datatype=ir.DataTypeInt(bits=32, signed=False))
    type_b = ir.DataTypeStruct(name="B", super=None, fields=[field_b_inner])

    field_a_inner = ir.Field(name="b_inst", datatype=ir.DataTypeRef(ref_name="B"))
    type_a = ir.DataTypeStruct(name="A", super=None, fields=[field_a_inner])

    ctxt = SwContext()
    # Insert A before B intentionally
    ctxt.type_m["A"] = type_a
    ctxt.type_m["B"] = type_b
    ctxt = TypeLowerPass().run(ctxt)

    bodies_text = "\n".join(ctxt.c_type_bodies.values())
    pos_a = bodies_text.find("typedef struct")
    # B should appear first — we check the keys come in the right relative order
    keys = list(ctxt.c_type_bodies.keys())
    assert keys.index("B") < keys.index("A")

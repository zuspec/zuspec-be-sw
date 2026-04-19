"""Unit tests for RTL RtlTypeMapper (mask-aware integer mapping)."""
import pytest
from zuspec.ir.core.data_type import DataTypeInt
from zuspec.be.sw.passes.rtl.type_mapper import RtlTypeMapper


@pytest.fixture
def tm():
    return RtlTypeMapper()


# ---------------------------------------------------------------------------
# map_type_with_mask
# ---------------------------------------------------------------------------

def test_bit1_type_and_mask(tm):
    """bit1 → uint8_t, mask 0x1u."""
    c_type, mask = tm.map_type_with_mask(DataTypeInt(bits=1, signed=False))
    assert c_type == "uint8_t"
    assert mask == "0x1u"


def test_bit8_exact(tm):
    """bit8 → uint8_t, no mask needed."""
    c_type, mask = tm.map_type_with_mask(DataTypeInt(bits=8, signed=False))
    assert c_type == "uint8_t"
    assert mask is None


def test_bit5(tm):
    """bit5 → uint8_t, mask 0x1Fu."""
    c_type, mask = tm.map_type_with_mask(DataTypeInt(bits=5, signed=False))
    assert c_type == "uint8_t"
    assert mask == "0x1Fu"


def test_bit16_exact(tm):
    """bit16 → uint16_t, no mask."""
    c_type, mask = tm.map_type_with_mask(DataTypeInt(bits=16, signed=False))
    assert c_type == "uint16_t"
    assert mask is None


def test_bit32_exact(tm):
    """bit32 → uint32_t, no mask."""
    c_type, mask = tm.map_type_with_mask(DataTypeInt(bits=32, signed=False))
    assert c_type == "uint32_t"
    assert mask is None


def test_bit64_exact(tm):
    """bit64 → uint64_t, no mask."""
    c_type, mask = tm.map_type_with_mask(DataTypeInt(bits=64, signed=False))
    assert c_type == "uint64_t"
    assert mask is None


def test_sub_word_mask_formula(tm):
    """Arbitrary widths 2–63 get correct masks."""
    cases = [
        (2,  "uint8_t",  "0x3u"),
        (7,  "uint8_t",  "0x7Fu"),
        (9,  "uint16_t", "0x1FFu"),
        (12, "uint16_t", "0xFFFu"),
        (17, "uint32_t", "0x1FFFFu"),
        (24, "uint32_t", "0xFFFFFFu"),
        (33, "uint64_t", "0x1FFFFFFFFu"),
        (63, "uint64_t", "0x7FFFFFFFFFFFFFFFu"),
    ]
    for bits, expected_type, expected_mask in cases:
        c_type, mask = tm.map_type_with_mask(DataTypeInt(bits=bits, signed=False))
        assert c_type == expected_type, f"bits={bits}: expected {expected_type}, got {c_type}"
        assert mask == expected_mask, f"bits={bits}: expected {expected_mask}, got {mask}"


# ---------------------------------------------------------------------------
# map_rtl_int_type
# ---------------------------------------------------------------------------

def test_signed_types(tm):
    """Signed integers pick correct container."""
    assert tm.map_rtl_int_type(DataTypeInt(bits=1, signed=True)) == "int8_t"
    assert tm.map_rtl_int_type(DataTypeInt(bits=8, signed=True)) == "int8_t"
    assert tm.map_rtl_int_type(DataTypeInt(bits=16, signed=True)) == "int16_t"
    assert tm.map_rtl_int_type(DataTypeInt(bits=32, signed=True)) == "int32_t"
    assert tm.map_rtl_int_type(DataTypeInt(bits=64, signed=True)) == "int64_t"

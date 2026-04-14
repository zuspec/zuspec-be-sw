"""
RTL TypeMapper — extends be-sw TypeMapper with mask-aware integer mapping.

The key addition for RTL code generation is ``map_type_with_mask()``, which
returns both the C storage type and a mask literal for sub-word fields.
"""
from __future__ import annotations

from typing import Optional, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.type_mapper import TypeMapper as SwTypeMapper


class RtlTypeMapper(SwTypeMapper):
    """Maps IR types to C types for RTL emission.

    Inherits all capabilities of the be-sw ``TypeMapper`` and adds
    ``map_type_with_mask()`` for sub-word (non-power-of-2-aligned) fields.
    """

    # Exact widths that map directly to C stdint types (no mask needed).
    _EXACT_WIDTHS = frozenset({8, 16, 32, 64})

    def map_rtl_int_type(self, dtype: ir.DataTypeInt) -> str:
        """Return the C storage type for an integer field.

        Sub-word widths use the *smallest* container that fits them.
        For example, ``bit5`` → ``uint8_t``.
        """
        bits = dtype.bits if dtype.bits > 0 else 32
        signed = dtype.signed

        if signed:
            if bits <= 8:
                return "int8_t"
            elif bits <= 16:
                return "int16_t"
            elif bits <= 32:
                return "int32_t"
            else:
                return "int64_t"
        else:
            if bits <= 8:
                return "uint8_t"
            elif bits <= 16:
                return "uint16_t"
            elif bits <= 32:
                return "uint32_t"
            else:
                return "uint64_t"

    def map_type_with_mask(
        self, dtype: ir.DataTypeInt
    ) -> Tuple[str, Optional[str]]:
        """Return ``(c_type, mask_literal)`` for an integer field.

        ``mask_literal`` is ``None`` when the width exactly matches the
        container (i.e., no masking is needed at read time).

        Examples
        --------
        >>> tm = TypeMapper()
        >>> tm.map_type_with_mask(DataTypeInt(bits=1, signed=False))
        ('uint8_t', '0x1u')
        >>> tm.map_type_with_mask(DataTypeInt(bits=8, signed=False))
        ('uint8_t', None)
        >>> tm.map_type_with_mask(DataTypeInt(bits=5, signed=False))
        ('uint8_t', '0x1Fu')
        """
        bits = dtype.bits if dtype.bits > 0 else 32
        c_type = self.map_rtl_int_type(dtype)

        if bits in self._EXACT_WIDTHS:
            return c_type, None

        # Compute mask = (1 << bits) - 1
        mask_val = (1 << bits) - 1
        # Format as hex literal with 'u' suffix (uppercase hex)
        mask_lit = f"0x{mask_val:X}u"
        return c_type, mask_lit

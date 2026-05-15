"""
CounterRecognitionPass — identify Counter sub-components in RTL components.

Populates ``ctx.counter_fields`` with a ``CounterInfo`` entry for each
recognized ``Counter``, ``ModuloCounter``, or ``WatchdogCounter``
sub-component field.

These fields are handled specially by ``WaitLowerPass`` and
``RtlCEmitPass``:
  * They are **not** emitted as sub-structs in the generated C struct.
  * ``await self.<ctr>.wait_for(N)`` / ``await self.<ctr>.wait_next()``
    are lowered to inline arithmetic using the counter's modulus and the
    component's clock period.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from zuspec.ir.core.data_type import DataTypeComponent

from zuspec.be.sw.ir.base import SwContext


@dataclass
class CounterInfo:
    """Metadata for one recognized Counter sub-component field.

    Attributes
    ----------
    field_name:
        Name of the Counter field in the parent component.
    modulus:
        Roll-over period of the counter.
        ``2 ** WIDTH`` for :class:`Counter`; ``PERIOD`` for
        :class:`ModuloCounter` / :class:`WatchdogCounter`.
    period_ps:
        Clock period in picoseconds (parent component's primary domain).
    is_modulo:
        ``True`` when the field is a ``ModuloCounter`` or
        ``WatchdogCounter`` (i.e. roll-over is explicit, not power-of-2).
    """

    field_name: str
    modulus: int
    period_ps: int
    is_modulo: bool


# Set of type names recognised as counter sub-components.
_COUNTER_TYPE_NAMES: frozenset = frozenset(
    ("Counter", "ModuloCounter", "WatchdogCounter")
)


class CounterRecognitionPass:
    """Walk the RTL component fields; record Counter sub-components.

    Run this pass **before** ``WaitLowerPass`` so that the counter
    metadata is available when ``RtlCEmitPass`` calls
    ``WaitLowerPass.lower_await`` at emit time.

    Populates
    ---------
    ctx.counter_fields : Dict[str, CounterInfo]
        Keyed by field name.
    ctx.all_co_waits_are_counter_jumps : bool
        Initialised to ``False``; updated by ``RtlCEmitPass`` after it
        determines whether every suspension point is a counter jump.
    """

    def run(self, ctx: SwContext) -> SwContext:
        ctx.counter_fields = {}
        ctx.all_co_waits_are_counter_jumps = False
        comp = ctx.rtl_component
        if comp is None:
            return ctx
        for f in comp.fields:
            if not isinstance(f.datatype, DataTypeComponent):
                continue
            if f.datatype.name not in _COUNTER_TYPE_NAMES:
                continue
            info = self._build_info(f, ctx)
            if info is not None:
                ctx.counter_fields[f.name] = info
        return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_info(
        self,
        field,
        ctx: SwContext,
    ) -> Optional[CounterInfo]:
        """Build a ``CounterInfo`` for *field*.

        Tries to read ``PERIOD`` / ``WIDTH`` from the default instance
        stored as a class attribute on the parent Python class.  Falls
        back to sub-component IR const fields if the class attribute is
        not available.
        """
        type_name = field.datatype.name
        is_modulo = type_name in ("ModuloCounter", "WatchdogCounter")

        # --- Try parent-class default instance first ---
        comp_cls = ctx.rtl_component_class
        ctr_inst = getattr(comp_cls, field.name, None) if comp_cls is not None else None

        if ctr_inst is not None:
            if is_modulo:
                period_val = getattr(ctr_inst, "PERIOD", None)
                if period_val is not None:
                    modulus = int(period_val)
                else:
                    modulus = 256  # fallback default
            else:
                width_val = getattr(ctr_inst, "WIDTH", None)
                if width_val is not None:
                    modulus = 1 << int(width_val)
                else:
                    modulus = 256  # fallback: WIDTH=8
        else:
            # --- Fallback: sub-component IR const fields ---
            const_map: Dict[str, int] = {}
            for sf in field.datatype.fields:
                if sf.is_const:
                    const_map[sf.name] = int(getattr(sf, "default_value", 0) or 0)
            if is_modulo:
                modulus = const_map.get("PERIOD") or 256
            else:
                width = const_map.get("WIDTH") or 8
                modulus = 1 << width

        if modulus <= 0:
            return None

        return CounterInfo(
            field_name=field.name,
            modulus=modulus,
            period_ps=ctx.rtl_domain_period_ps,
            is_modulo=is_modulo,
        )

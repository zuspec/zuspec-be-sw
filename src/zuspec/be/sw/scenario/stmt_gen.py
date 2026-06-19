"""Scenario statement/expression generation.

A thin subclass of the existing :class:`~zuspec.be.sw.stmt_generator.StmtGenerator`
that adds the one mapping the PSS path needs and the datamodel path lacks:
``message(...)`` / ``print(...)`` → ``fprintf``.  Everything else (field refs,
binops, slices, …) is delegated to the base generator unchanged, so the
datamodel-driven ``CGenerator`` is untouched (impl-plan §1 / C7).

The base generator otherwise lowers ``self.<attr>`` → ``self-><attr>``, which is
exactly what an action body needs (``self`` is the action struct).
"""
from __future__ import annotations

from zuspec.be.sw.stmt_generator import StmtGenerator

# ``zuspec.dataclasses.ir`` re-exports the same classes as ``zuspec.ir.core``;
# the base generator's isinstance checks use that module, so we match it.
from zuspec.dataclasses import ir


class _Unsupported(Exception):
    """Raised on a scenario construct the Phase-2 emitter cannot lower."""


def _c_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# fe-pss emits comparisons / boolean ops as ``ExprBin`` (the datamodel frontend
# uses ``ExprCompare``/``ExprBool`` instead), so the base ``_get_dm_binop`` map —
# arithmetic/bitwise only — returns "?" for them.  Extend it here.
_EXTRA_BINOPS = {
    "Eq": "==", "NotEq": "!=", "Lt": "<", "LtE": "<=", "Gt": ">", "GtE": ">=",
    "And": "&&", "Or": "||",
}


class ScenarioStmtGenerator(StmtGenerator):
    """``StmtGenerator`` + ``message``/``print`` → ``fprintf`` + comparison/
    boolean ``ExprBin`` operator support (for fe-pss-style conditions) +
    inline ``solve`` import calls (synchronous host re-entry)."""

    def __init__(self, *args, solve_imports=None, **kwargs):
        super().__init__(*args, **kwargs)
        # name -> fn_id for non-blocking (solve) imports, rendered inline.
        self._solve_imports = solve_imports or {}
        from zuspec.be.sw.type_mapper import TypeMapper
        self._tmap = TypeMapper()

    def _gen_dm_stmt(self, stmt) -> str:  # overrides base
        # Emit a typed declaration for an exec-body local (`bit[32] v = ...`);
        # the base generator assumes locals are declared elsewhere (the
        # datamodel frame path), which the scenario path doesn't run.
        if (isinstance(stmt, ir.StmtAnnAssign) and stmt.value is not None
                and isinstance(stmt.target, ir.ExprRefLocal)
                and stmt.annotation is not None):
            try:
                ctype = self._tmap.map_type(stmt.annotation)
            except Exception:
                ctype = None
            if ctype:
                target = self._gen_dm_expr(stmt.target)
                value = self._gen_dm_expr(stmt.value)
                return "%s %s = %s;" % (ctype, target, value)
        return super()._gen_dm_stmt(stmt)

    def _get_dm_binop(self, op) -> str:
        name = getattr(op, "name", None)
        if name in _EXTRA_BINOPS:
            return _EXTRA_BINOPS[name]
        return super()._get_dm_binop(op)

    def _gen_dm_call(self, expr) -> str:  # noqa: D401 - overrides base
        func = expr.func
        if (isinstance(func, ir.ExprAttribute)
                and isinstance(func.value, ir.TypeExprRefSelf)):
            if func.attr in ("message", "print"):
                return self._gen_message(
                    expr.args, is_message=(func.attr == "message"))
            if func.attr in self._solve_imports:
                fn_id = self._solve_imports[func.attr]
                argv = [self._gen_dm_expr(a) for a in expr.args]
                tail = "".join(", (int64_t)(%s)" % a for a in argv)
                return ("zsp_scenario_call_solve(%d, %d%s)"
                        % (fn_id, len(argv), tail))
        return super()._gen_dm_call(expr)

    # ------------------------------------------------------------------
    def _gen_message(self, args, is_message: bool) -> str:
        """Lower ``self.message(verbosity, fmt, vals...)`` / ``self.print(fmt,
        vals...)`` to ``fprintf(stdout, "fmt\\n", vals...)``.

        The PSS ``message`` format string already uses C-style conversion
        specifiers (``%x``, ``%d``), so it passes through verbatim.
        """
        if is_message:
            # args[0] = verbosity (ignored in iteration 1); args[1] = format.
            if len(args) < 2:
                raise _Unsupported("message() requires a verbosity and a format")
            fmt_expr = args[1]
            value_args = args[2:]
        else:
            if len(args) < 1:
                raise _Unsupported("print() requires a format")
            fmt_expr = args[0]
            value_args = args[1:]

        if not isinstance(fmt_expr, ir.ExprConstant) or not isinstance(fmt_expr.value, str):
            raise _Unsupported(
                "message/print format must be a string literal in iteration 1")

        fmt = _c_escape(fmt_expr.value)
        vals = [self._gen_dm_expr(a) for a in value_args]
        tail = ("" if not vals else ", " + ", ".join(vals))
        return 'fprintf(stdout, "%s\\n"%s)' % (fmt, tail)

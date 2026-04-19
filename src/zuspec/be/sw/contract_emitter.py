"""C contract emitter for zuspec-be-sw.

Translates ``@constraint.requires`` and ``@constraint.ensures`` methods on an
action class into C assertion/assumption code that can be injected around the
action body in generated C.

For each ``@constraint.requires`` method:
    * ``__builtin_assume(expr)`` in release builds (optimizer hint)
    * ``assert(expr)`` wrapped in ``#ifndef NDEBUG`` / ``#endif``

For each ``@constraint.ensures`` method:
    * ``assert(expr)`` wrapped in ``#ifndef NDEBUG`` / ``#endif``

Typical use::

    from zuspec.be.sw.contract_emitter import ActionContractEmitter

    emitter = ActionContractEmitter()
    pre_lines  = emitter.emit_requires(MyAction)   # before body()
    post_lines = emitter.emit_ensures(MyAction)    # after body()

The returned lists contain complete C lines (no trailing newline).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Lazy import helpers
# ---------------------------------------------------------------------------

def _get_constraint_parser():
    from zuspec.dataclasses.constraint_parser import ConstraintParser
    return ConstraintParser


# ---------------------------------------------------------------------------
# Constraint IR → C expression translator
# ---------------------------------------------------------------------------

class _ConstraintExprToC:
    """Translate a constraint expression dict to a C expression string.

    Supports the subset of IR nodes produced by
    :meth:`~zuspec.dataclasses.constraint_parser.ConstraintParser.parse_constraint`:
    ``attribute``, ``constant``, ``compare``, ``bool_op``, ``bin_op``,
    ``unary_op``, and ``implies``.
    """

    _COMPARE_OPS = {
        '==': '==', '!=': '!=',
        '<':  '<',  '<=': '<=',
        '>':  '>',  '>=': '>=',
    }
    _BOOL_OPS  = {'and': '&&', 'or': '||'}
    _BIN_OPS   = {
        '+': '+', '-': '-', '*': '*', '/': '/', '%': '%',
        '&': '&', '|': '|', '^': '^', '<<': '<<', '>>': '>>',
    }
    _UNARY_OPS = {'not': '!', 'invert': '~', 'usub': '-'}

    def __init__(self, field_prefix: str = "") -> None:
        """
        Args:
            field_prefix: Prepended to every field name (``attr`` node).
                Use ``"self->"`` for struct-pointer access inside a C function.
        """
        self._prefix = field_prefix

    def translate(self, node: Dict[str, Any]) -> Optional[str]:
        """Return a C expression string for *node*, or ``None`` on failure."""
        try:
            return self._tr(node)
        except Exception:
            return None

    def _tr(self, node: Dict[str, Any]) -> str:
        t = node.get('type')
        if t == 'attribute':
            # ``self.field`` → ``<prefix>field`` (use the ``attr`` key)
            return f"{self._prefix}{node.get('attr', '?')}"
        if t == 'constant':
            return str(node.get('value', 0))
        if t == 'compare':
            left = self._tr(node['left'])
            ops = node.get('ops', [])
            comps = node.get('comparators', [])
            parts = [left]
            for op, rhs in zip(ops, comps):
                c_op = self._COMPARE_OPS.get(op, op)
                parts.append(f"{c_op} {self._tr(rhs)}")
            return '(' + ' '.join(parts) + ')'
        if t == 'bool_op':
            op = self._BOOL_OPS.get(node.get('op', 'and'), '&&')
            parts = [self._tr(v) for v in node.get('values', [])]
            return '(' + f' {op} '.join(parts) + ')'
        if t == 'bin_op':
            op = self._BIN_OPS.get(node.get('op', '+'), node.get('op', '+'))
            return f"({self._tr(node['left'])} {op} {self._tr(node['right'])})"
        if t == 'unary_op':
            op = self._UNARY_OPS.get(node.get('op', 'not'), '!')
            return f"({op}{self._tr(node['operand'])})"
        if t == 'implies':
            # ``A → B`` becomes ``(!A || B)`` in C
            antecedent = self._tr(node['antecedent'])
            consequent = node.get('consequent', [])
            if isinstance(consequent, list) and consequent:
                cons_str = ' && '.join(self._tr(c) for c in consequent)
            elif isinstance(consequent, dict):
                cons_str = self._tr(consequent)
            else:
                cons_str = '1'
            return f"(!{antecedent} || {cons_str})"
        raise ValueError(f"Unsupported IR node type: {t!r}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ActionContractEmitter:
    """Emit C assertion / assumption code for action contracts.

    Instantiate once and call :meth:`emit_requires` / :meth:`emit_ensures`
    for each action class.
    """

    def __init__(self, field_prefix: str = "") -> None:
        """
        Args:
            field_prefix: String prepended to every field name in C expressions.
                Use ``"self->"`` when generating code inside a function that
                receives the action struct as ``ActionName_t *self``.  The
                default ``""`` emits bare field names (suitable for unit tests
                and standalone assertions).
        """
        self._xlator = _ConstraintExprToC(field_prefix=field_prefix)

    def emit_requires(self, action_cls: type) -> List[str]:
        """Return C lines asserting all ``@constraint.requires`` expressions.

        Lines are:
        1. A ``__builtin_assume(expr)`` for static analysis / optimizers.
        2. ``#ifndef NDEBUG``
        3. ``assert(expr);``
        4. ``#endif``

        Returns an empty list if the class has no ``requires`` constraints.
        """
        return self._emit_role(action_cls, 'requires')

    def emit_ensures(self, action_cls: type) -> List[str]:
        """Return C lines asserting all ``@constraint.ensures`` expressions.

        Lines are:
        1. ``#ifndef NDEBUG``
        2. ``assert(expr);``
        3. ``#endif``

        Returns an empty list if the class has no ``ensures`` constraints.
        """
        return self._emit_role(action_cls, 'ensures')

    # ------------------------------------------------------------------

    def _emit_role(self, action_cls: type, role: str) -> List[str]:
        ConstraintParser = _get_constraint_parser()
        parser = ConstraintParser()

        lines: List[str] = []
        for attr_name, method in vars(action_cls).items():
            if not (callable(method) and getattr(method, '_is_constraint', False)):
                continue
            if getattr(method, '_constraint_role', None) != role:
                continue

            try:
                parsed = parser.parse_constraint(method)
            except Exception:
                continue

            for expr in parsed.get('exprs', []):
                c_expr = self._xlator.translate(expr)
                if c_expr is None:
                    continue
                if role == 'requires':
                    lines.append(f"__builtin_assume({c_expr});")
                lines.append("#ifndef NDEBUG")
                lines.append(f"assert({c_expr});")
                lines.append("#endif")

        return lines

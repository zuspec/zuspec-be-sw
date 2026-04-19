"""T-P9: Tests for ActionContractEmitter in zuspec-be-sw.

These tests verify that the contract emitter correctly generates C assertion
and assumption code for @constraint.requires and @constraint.ensures methods.

Fixture action classes must be at module level so inspect.getsource() works.
"""
import sys
import os

_pkg = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
_dc  = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'zuspec-dataclasses', 'src')
sys.path.insert(0, _pkg)
sys.path.insert(1, _dc)

import pytest
from zuspec.dataclasses.decorators import constraint as _constraint
from zuspec.be.sw.contract_emitter import ActionContractEmitter, _ConstraintExprToC


# ---------------------------------------------------------------------------
# Module-level fixture action classes
# ---------------------------------------------------------------------------

class _ActionWithRequires:
    @_constraint.requires
    def req_positive(self):
        self.value > 0

    @_constraint.requires
    def req_bounded(self):
        self.value < 100


class _ActionWithEnsures:
    @_constraint.ensures
    def ens_bounded(self):
        self.result < 200


class _ActionBothRoles:
    @_constraint.requires
    def req_in(self):
        self.inp < 50

    @_constraint.ensures
    def ens_out(self):
        self.out < 100


class _ActionNoRole:
    @_constraint
    def c_range(self):
        self.x < 128


class _ActionEmpty:
    pass


# ---------------------------------------------------------------------------
# T-P9a: emit_requires() tests
# ---------------------------------------------------------------------------

class TestEmitRequires:
    def setup_method(self):
        self.emitter = ActionContractEmitter()

    def test_requires_produces_output(self):
        lines = self.emitter.emit_requires(_ActionWithRequires)
        assert len(lines) > 0

    def test_requires_contains_assert(self):
        lines = self.emitter.emit_requires(_ActionWithRequires)
        assert any('assert(' in l for l in lines)

    def test_requires_contains_builtin_assume(self):
        lines = self.emitter.emit_requires(_ActionWithRequires)
        assert any('__builtin_assume(' in l for l in lines)

    def test_requires_has_ndebug_guard(self):
        lines = self.emitter.emit_requires(_ActionWithRequires)
        assert '#ifndef NDEBUG' in lines
        assert '#endif' in lines

    def test_requires_ndebug_surrounds_assert(self):
        lines = self.emitter.emit_requires(_ActionWithRequires)
        ndebug_idx = lines.index('#ifndef NDEBUG')
        endif_idx  = lines.index('#endif', ndebug_idx)
        assert any('assert(' in lines[i] for i in range(ndebug_idx, endif_idx))

    def test_no_requires_returns_empty(self):
        lines = self.emitter.emit_requires(_ActionWithEnsures)
        assert lines == []

    def test_no_role_not_emitted_as_requires(self):
        lines = self.emitter.emit_requires(_ActionNoRole)
        assert lines == []

    def test_empty_class_returns_empty(self):
        lines = self.emitter.emit_requires(_ActionEmpty)
        assert lines == []

    def test_multiple_requires_methods_all_emitted(self):
        lines = self.emitter.emit_requires(_ActionWithRequires)
        # Two requires methods → two sets of (assume + #ifndef NDEBUG + assert + #endif)
        assert lines.count('#ifndef NDEBUG') == 2


# ---------------------------------------------------------------------------
# T-P9b: emit_ensures() tests
# ---------------------------------------------------------------------------

class TestEmitEnsures:
    def setup_method(self):
        self.emitter = ActionContractEmitter()

    def test_ensures_produces_output(self):
        lines = self.emitter.emit_ensures(_ActionWithEnsures)
        assert len(lines) > 0

    def test_ensures_contains_assert(self):
        lines = self.emitter.emit_ensures(_ActionWithEnsures)
        assert any('assert(' in l for l in lines)

    def test_ensures_has_ndebug_guard(self):
        lines = self.emitter.emit_ensures(_ActionWithEnsures)
        assert '#ifndef NDEBUG' in lines

    def test_ensures_no_builtin_assume(self):
        lines = self.emitter.emit_ensures(_ActionWithEnsures)
        assert not any('__builtin_assume' in l for l in lines)

    def test_no_ensures_returns_empty(self):
        lines = self.emitter.emit_ensures(_ActionWithRequires)
        assert lines == []


# ---------------------------------------------------------------------------
# T-P9c: expression content tests
# ---------------------------------------------------------------------------

class TestExpressionContent:
    def setup_method(self):
        self.emitter = ActionContractEmitter()

    def test_field_name_in_requires(self):
        lines = self.emitter.emit_requires(_ActionWithRequires)
        combined = ' '.join(lines)
        assert 'value' in combined

    def test_field_name_in_ensures(self):
        lines = self.emitter.emit_ensures(_ActionWithEnsures)
        combined = ' '.join(lines)
        assert 'result' in combined

    def test_both_roles_independent(self):
        req_lines = self.emitter.emit_requires(_ActionBothRoles)
        ens_lines = self.emitter.emit_ensures(_ActionBothRoles)
        assert req_lines  # has requires
        assert ens_lines  # has ensures
        # ensures should not appear in requires output
        assert not any('ens_out' in l for l in req_lines)


# ---------------------------------------------------------------------------
# T-P9d: _ConstraintExprToC translator unit tests
# ---------------------------------------------------------------------------

class TestConstraintExprToC:
    def _tr(self, node):
        return _ConstraintExprToC().translate(node)

    def test_attribute(self):
        result = self._tr({'type': 'attribute', 'value': 'self', 'attr': 'foo'})
        assert result == 'foo'

    def test_constant(self):
        assert self._tr({'type': 'constant', 'value': 42}) == '42'

    def test_compare_eq(self):
        node = {
            'type': 'compare',
            'left': {'type': 'attribute', 'attr': 'x'},
            'ops': ['=='],
            'comparators': [{'type': 'constant', 'value': 5}],
        }
        assert self._tr(node) == '(x == 5)'

    def test_compare_lt(self):
        node = {
            'type': 'compare',
            'left': {'type': 'attribute', 'attr': 'v'},
            'ops': ['<'],
            'comparators': [{'type': 'constant', 'value': 100}],
        }
        assert '< 100' in self._tr(node)

    def test_bool_op_and(self):
        node = {
            'type': 'bool_op',
            'op': 'and',
            'values': [
                {'type': 'attribute', 'attr': 'a'},
                {'type': 'attribute', 'attr': 'b'},
            ],
        }
        result = self._tr(node)
        assert '&&' in result
        assert 'a' in result and 'b' in result

    def test_bool_op_or(self):
        node = {
            'type': 'bool_op',
            'op': 'or',
            'values': [
                {'type': 'attribute', 'attr': 'x'},
                {'type': 'attribute', 'attr': 'y'},
            ],
        }
        result = self._tr(node)
        assert '||' in result

    def test_unary_not(self):
        node = {
            'type': 'unary_op',
            'op': 'not',
            'operand': {'type': 'attribute', 'attr': 'en'},
        }
        result = self._tr(node)
        assert '!en' in result

    def test_implies_becomes_or(self):
        node = {
            'type': 'implies',
            'antecedent': {'type': 'attribute', 'attr': 'cond'},
            'consequent': {'type': 'attribute', 'attr': 'result'},
        }
        result = self._tr(node)
        assert '||' in result
        assert '!cond' in result

    def test_bad_node_returns_none(self):
        assert self._tr({'type': 'undefined_xyz'}) is None


# ---------------------------------------------------------------------------
# T-P9e: field_prefix tests
# ---------------------------------------------------------------------------

class TestFieldPrefix:
    """Verify that field_prefix is prepended to attribute names."""

    def test_default_no_prefix(self):
        emitter = ActionContractEmitter()
        lines = emitter.emit_requires(_ActionWithRequires)
        # With no prefix, bare field names like 'value > 0' should appear
        assert any('value' in l for l in lines)
        assert not any('self->value' in l for l in lines)

    def test_struct_ptr_prefix(self):
        emitter = ActionContractEmitter(field_prefix="self->")
        lines = emitter.emit_requires(_ActionWithRequires)
        assert any('self->value' in l for l in lines)

    def test_prefix_in_ensures(self):
        emitter = ActionContractEmitter(field_prefix="self->")
        lines = emitter.emit_ensures(_ActionWithEnsures)
        assert any('self->result' in l for l in lines)

    def test_custom_prefix(self):
        emitter = ActionContractEmitter(field_prefix="act.")
        lines = emitter.emit_requires(_ActionWithRequires)
        assert any('act.value' in l for l in lines)

    def test_xlator_prefix_attribute(self):
        xlator = _ConstraintExprToC(field_prefix="p->")
        node = {'type': 'attribute', 'attr': 'x'}
        assert xlator.translate(node) == 'p->x'

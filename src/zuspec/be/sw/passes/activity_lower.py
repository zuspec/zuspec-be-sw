"""ActivityLowerPass — lower activity_ir to SW scheduler nodes."""
from __future__ import annotations

from typing import List, Optional

from zuspec.dataclasses import ir
from zuspec.dataclasses.ir.activity import (
    ActivitySequenceBlock,
    ActivityParallel,
    ActivitySchedule,
    ActivityAtomic,
    ActivityTraversal,
    ActivityAnonTraversal,
    ActivitySuper,
    ActivityRepeat,
    ActivityDoWhile,
    ActivityWhileDo,
    ActivityForeach,
    ActivityReplicate,
    ActivitySelect,
    ActivityIfElse,
    ActivityMatch,
    ActivityConstraint,
    ActivityBind,
    ActivityStmt,
    SelectBranch,
)
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.activity import (
    SwSchedulerNode,
    SwActionExec,
    SwSeqBlock,
    SwParBlock,
    SwSelectNode,
    SwSelectBranch,
    SwNode,
)
from zuspec.be.sw.pipeline import SwPass


class ActivityLowerPass(SwPass):
    """For each ``DataTypeClass`` with ``activity_ir`` set, produce a
    ``SwSchedulerNode`` and store it in ``ctxt.sw_nodes[type_name]``.
    """

    def run(self, ctxt: SwContext) -> SwContext:
        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, ir.DataTypeStruct):
                continue
            # activity_ir may be on the DataTypeClass, or on the Python type
            activity_ir = getattr(dtype, "activity_ir", None)
            if activity_ir is None and dtype.py_type is not None:
                activity_ir = getattr(dtype.py_type, "__activity__", None)
            if not activity_ir:
                continue
            sched = self._lower_action(dtype, activity_ir)
            ctxt.sw_nodes.setdefault(type_name, []).append(sched)
        return ctxt

    # ------------------------------------------------------------------
    # Top-level
    # ------------------------------------------------------------------

    def _lower_action(
        self,
        action_type: ir.DataTypeStruct,
        activity_ir: ActivitySequenceBlock,
    ) -> SwSchedulerNode:
        root = self._lower_seq(activity_ir.stmts, [])
        return SwSchedulerNode(action_type=action_type, root=root)

    # ------------------------------------------------------------------
    # Statement dispatching
    # ------------------------------------------------------------------

    def _lower_stmts(
        self,
        stmts: List[ActivityStmt],
        pending_constraints: List,
    ) -> SwNode:
        """Lower a list of stmts, returning a SwSeqBlock (or single node)."""
        children = self._lower_stmts_list(stmts, pending_constraints)
        if len(children) == 1:
            return children[0]
        return SwSeqBlock(children=children)

    def _lower_stmts_list(
        self,
        stmts: List[ActivityStmt],
        pending_constraints: List,
    ) -> List[SwNode]:
        children: List[SwNode] = []
        for stmt in stmts:
            node = self._lower_stmt(stmt, pending_constraints)
            if node is not None:
                children.append(node)
        return children

    def _lower_seq(
        self,
        stmts: List[ActivityStmt],
        pending_constraints: List,
    ) -> SwSeqBlock:
        children = self._lower_stmts_list(stmts, pending_constraints)
        return SwSeqBlock(children=children)

    def _lower_stmt(
        self,
        stmt: ActivityStmt,
        pending_constraints: List,
    ) -> Optional[SwNode]:
        if isinstance(stmt, ActivitySequenceBlock):
            return self._lower_seq(stmt.stmts, [])

        if isinstance(stmt, (ActivityParallel, ActivitySchedule)):
            join = "all"
            if stmt.join_spec:
                join = stmt.join_spec.kind or "all"
            children = self._lower_stmts_list(stmt.stmts, [])
            return SwParBlock(children=children, join=join)

        if isinstance(stmt, ActivityAtomic):
            return self._lower_seq(stmt.stmts, [])

        if isinstance(stmt, ActivityTraversal):
            exec_node = SwActionExec(
                handle_name=stmt.handle,
                solve_constraints=list(stmt.inline_constraints),
            )
            if pending_constraints:
                exec_node.solve_constraints.extend(pending_constraints)
                pending_constraints.clear()
            return exec_node

        if isinstance(stmt, ActivityAnonTraversal):
            action_type = None
            if stmt.action_type_cls is not None:
                # Look up via py_type
                pass
            exec_node = SwActionExec(
                handle_name=stmt.label,
                solve_constraints=list(stmt.inline_constraints),
            )
            if pending_constraints:
                exec_node.solve_constraints.extend(pending_constraints)
                pending_constraints.clear()
            return exec_node

        if isinstance(stmt, ActivitySuper):
            return SwActionExec(handle_name="__super__")

        if isinstance(stmt, ActivityRepeat):
            inner = self._lower_seq(stmt.body, [])
            # A repeat is modeled as a sequential block with one child
            # that carries a loop annotation.  We wrap it in a SwSeqBlock
            # with a special marker node for code generation to handle.
            return _SwRepeat(count=stmt.count, index_var=stmt.index_var, body=inner)

        if isinstance(stmt, ActivityDoWhile):
            inner = self._lower_seq(stmt.body, [])
            return _SwDoWhile(condition=stmt.condition, body=inner)

        if isinstance(stmt, ActivityWhileDo):
            inner = self._lower_seq(stmt.body, [])
            return _SwWhileDo(condition=stmt.condition, body=inner)

        if isinstance(stmt, ActivityForeach):
            inner = self._lower_seq(stmt.body, [])
            return _SwForeach(
                iterator=stmt.iterator,
                collection=stmt.collection,
                index_var=stmt.index_var,
                body=inner,
            )

        if isinstance(stmt, ActivityReplicate):
            # Each replicate copy gets its own SwSeqBlock clone.
            # We model this as a SwParBlock with select join.
            inner = self._lower_seq(stmt.body, [])
            return _SwReplicate(count=stmt.count, index_var=stmt.index_var, body=inner)

        if isinstance(stmt, ActivitySelect):
            branches = []
            for branch in stmt.branches:
                body_node = self._lower_seq(branch.body, [])
                branches.append(
                    SwSelectBranch(
                        guard=branch.guard,
                        weight=branch.weight,
                        body=body_node,
                    )
                )
            return SwSelectNode(branches=branches)

        if isinstance(stmt, ActivityIfElse):
            if_body = self._lower_seq(stmt.if_body, [])
            else_body = self._lower_seq(stmt.else_body, []) if stmt.else_body else None
            return _SwIfElse(condition=stmt.condition, if_body=if_body, else_body=else_body)

        if isinstance(stmt, ActivityMatch):
            cases = []
            for case in stmt.cases:
                body_node = self._lower_seq(case.body, [])
                cases.append(_SwMatchCase(pattern=case.pattern, body=body_node))
            return _SwMatch(subject=stmt.subject, cases=cases)

        if isinstance(stmt, ActivityConstraint):
            # Constraints are deferred to the next traversal node.
            pending_constraints.extend(stmt.constraints)
            return None

        if isinstance(stmt, ActivityBind):
            # Bindings are not lowered to a scheduler node.
            return None

        return None


# ------------------------------------------------------------------
# Extended SW IR nodes (activity-lower-specific; not in the public IR)
# ------------------------------------------------------------------

import dataclasses as dc
from typing import Any


@dc.dataclass(kw_only=True)
class _SwRepeat(SwNode):
    count: Optional[ir.Expr] = dc.field(default=None)
    index_var: Optional[str] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class _SwDoWhile(SwNode):
    condition: Optional[ir.Expr] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class _SwWhileDo(SwNode):
    condition: Optional[ir.Expr] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class _SwForeach(SwNode):
    iterator: Optional[str] = dc.field(default=None)
    collection: Optional[Any] = dc.field(default=None)
    index_var: Optional[str] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class _SwReplicate(SwNode):
    count: Optional[ir.Expr] = dc.field(default=None)
    index_var: Optional[str] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class _SwIfElse(SwNode):
    condition: Optional[ir.Expr] = dc.field(default=None)
    if_body: Optional[SwNode] = dc.field(default=None)
    else_body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class _SwMatchCase(SwNode):
    pattern: Optional[ir.Expr] = dc.field(default=None)
    body: Optional[SwNode] = dc.field(default=None)


@dc.dataclass(kw_only=True)
class _SwMatch(SwNode):
    subject: Optional[ir.Expr] = dc.field(default=None)
    cases: List[_SwMatchCase] = dc.field(default_factory=list)

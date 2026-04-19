"""AsyncLowerPass — classify async functions and split them into coroutine frames.

Two sub-steps:

Step A — Classification
  _classify(func, ctxt, sync_map) -> bool
  True if no ExprAwait anywhere in the body AND no call to a non-sync-
  convertible function (fixed-point iteration over the call graph within
  the context) AND not a DataTypeProtocol method AND not is_import.

Step B — Coroutine splitting
  _split(func, comp_name) -> SwCoroutineFrame
  Linear scan of func.body. Each ExprAwait ends the current SwContinuation
  and starts a new one. A simple liveness pass decides which locals cross a
  suspend point (stored in locals_struct vs plain locals).

Whole pass
  AsyncLowerPass.run(ctxt) -> SwContext
  For each component function that is_async:
  - Classify → if sync_convertible: func.metadata['sync_convertible'] = True
  - Otherwise: build SwCoroutineFrame, append to ctxt.sw_nodes[comp_name]
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from zuspec.dataclasses import ir
from zuspec.be.sw.ir.base import SwContext
from zuspec.be.sw.ir.coroutine import (
    SwCoroutineFrame,
    SwContinuation,
    SwLocalVar,
    SwSuspendCall,
    SwSuspendCompletion,
    SwSuspendFifoPop,
    SwSuspendFifoPush,
    SwSuspendMutex,
    SwSuspendSpawn,
    SwSuspendWait,
    SwSuspendPoint,
)
from zuspec.be.sw.pipeline import SwPass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_await(node) -> bool:
    """Recursively check whether *node* (Expr or Stmt) contains ExprAwait."""
    if isinstance(node, ir.ExprAwait):
        return True
    for child in _children(node):
        if _has_await(child):
            return True
    return False


def _collect_awaits(stmts: list) -> List[Tuple[int, ir.ExprAwait]]:
    """Return a flat list of (stmt_index, ExprAwait) pairs from *stmts*.

    We only look at top-level awaits within each statement; nested awaits
    (e.g., inside an if-branch) are also collected via DFS.
    """
    result: List[Tuple[int, ir.ExprAwait]] = []
    for i, stmt in enumerate(stmts):
        for aw in _find_awaits(stmt):
            result.append((i, aw))
    return result


def _find_awaits(node) -> List[ir.ExprAwait]:
    """DFS, collect ExprAwait nodes (does not recurse into already-found ones)."""
    if isinstance(node, ir.ExprAwait):
        return [node]
    found = []
    for child in _children(node):
        found.extend(_find_awaits(child))
    return found


def _children(node):
    """Yield direct child nodes (Stmt/Expr) of *node*."""
    if not hasattr(node, "__dataclass_fields__"):
        return
    for f in node.__dataclass_fields__.values():
        val = getattr(node, f.name, None)
        if val is None:
            continue
        if isinstance(val, (ir.Stmt, ir.Expr)):
            yield val
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, (ir.Stmt, ir.Expr)):
                    yield item


def _called_names(func: ir.Function) -> Set[str]:
    """Collect all simple function / method names called in func.body."""
    names: Set[str] = set()
    for stmt in func.body:
        _collect_calls(stmt, names)
    return names


def _collect_calls(node, names: Set[str]) -> None:
    if isinstance(node, ir.ExprCall):
        fn = node.func
        if isinstance(fn, ir.ExprAttribute):
            names.add(fn.attr)
        elif isinstance(fn, (ir.ExprRefLocal, ir.ExprRefUnresolved)):
            names.add(fn.name)
    for child in _children(node):
        _collect_calls(child, names)


def _assigns_in_stmts(stmts: list) -> Set[str]:
    """Names of all local variables assigned in *stmts* (shallow scan)."""
    names: Set[str] = set()
    for stmt in stmts:
        if isinstance(stmt, (ir.StmtAssign, ir.StmtAnnAssign)):
            target = getattr(stmt, "target", None) or getattr(stmt, "targets", [None])[0]
            if isinstance(target, ir.ExprRefLocal):
                names.add(target.name)
        elif isinstance(stmt, ir.StmtAssign):
            for t in getattr(stmt, "targets", []):
                if isinstance(t, ir.ExprRefLocal):
                    names.add(t.name)
    return names


def _refs_in_stmts(stmts: list) -> Set[str]:
    """Names of all ExprRefLocal occurrences in *stmts* (shallow scan)."""
    names: Set[str] = set()
    for stmt in stmts:
        _collect_refs(stmt, names)
    return names


def _collect_refs(node, names: Set[str]) -> None:
    if isinstance(node, ir.ExprRefLocal):
        names.add(node.name)
    for child in _children(node):
        _collect_refs(child, names)


# ---------------------------------------------------------------------------
# Step A — Classification
# ---------------------------------------------------------------------------

def _classify_function(
    func: ir.Function,
    comp_name: str,
    proto_methods: Set[str],
    sync_map: Dict[str, bool],
) -> bool:
    """Return True if *func* can be safely converted to sync.

    Arguments
    ----------
    func:
        The async function to classify.
    comp_name:
        Qualified name of the owning component (used for sync_map keys).
    proto_methods:
        Set of ``"TypeName.method_name"`` strings from ``DataTypeProtocol``
        types — these must always remain async.
    sync_map:
        Mutable map from ``"CompName.funcname"`` → bool; updated in-place.
    """
    key = f"{comp_name}.{func.name}"

    # Protocol interface methods are always async
    if key in proto_methods:
        sync_map[key] = False
        return False

    # Import functions are always async
    if func.is_import:
        sync_map[key] = False
        return False

    # Any await expression in the body → not sync convertible
    for stmt in func.body:
        if _has_await(stmt):
            sync_map[key] = False
            return False

    # If any called function is not sync-convertible, this one isn't either.
    for name in _called_names(func):
        full = f"{comp_name}.{name}"
        if sync_map.get(full) is False:
            sync_map[key] = False
            return False

    sync_map[key] = True
    return True


def _build_proto_methods(ctxt: SwContext) -> Set[str]:
    result: Set[str] = set()
    for type_name, dtype in ctxt.type_m.items():
        if isinstance(dtype, ir.DataTypeProtocol):
            for method in dtype.methods:
                result.add(f"{type_name}.{method.name}")
    return result


def _classify_all(ctxt: SwContext) -> Dict[str, bool]:
    """Fixed-point classify all async functions in *ctxt*."""
    proto_methods = _build_proto_methods(ctxt)
    sync_map: Dict[str, bool] = {}

    # Pre-mark all protocol methods as non-sync-convertible
    for key in proto_methods:
        sync_map[key] = False

    changed = True
    while changed:
        changed = False
        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, (ir.DataTypeComponent, ir.DataTypeClass)):
                continue
            for func in getattr(dtype, "functions", []):
                if not getattr(func, "is_async", False):
                    continue
                key = f"{type_name}.{func.name}"
                prev = sync_map.get(key)
                new_val = _classify_function(func, type_name, proto_methods, sync_map)
                if sync_map.get(key) != prev:
                    changed = True
    return sync_map


# ---------------------------------------------------------------------------
# Step B — Coroutine splitting
# ---------------------------------------------------------------------------

def _classify_await(await_expr: ir.ExprAwait) -> SwSuspendPoint:
    """Map an ``ExprAwait`` to the appropriate ``SwSuspendPoint`` subclass."""
    inner = await_expr.value

    # zdc.Completion await → SwSuspendCompletion
    if hasattr(ir, "CompletionAwaitExpr") and isinstance(inner, ir.CompletionAwaitExpr):
        # completion_expr is the expression that yields the Completion object.
        # Try to extract a simple field name for the C runtime macro.
        completion_field = _attr_base_name(inner.completion_expr) or "completion"
        return SwSuspendCompletion(
            completion_field=completion_field,
            elem_type=getattr(inner, "result_type", None),
        )

    # zdc.Queue.get() → SwSuspendFifoPop (queue variant)
    if hasattr(ir, "QueueGetExpr") and isinstance(inner, ir.QueueGetExpr):
        fifo_field = _attr_base_name(inner.queue_expr) or "queue"
        return SwSuspendFifoPop(
            fifo_field=fifo_field,
        )

    # wait(duration) / delay(duration)
    if isinstance(inner, ir.ExprCall):
        fn = inner.func
        fn_name = None
        if isinstance(fn, ir.ExprAttribute):
            fn_name = fn.attr
        elif isinstance(fn, (ir.ExprRefLocal, ir.ExprRefUnresolved)):
            fn_name = fn.name

        if fn_name in ("wait", "delay"):
            arg = inner.args[0] if inner.args else None
            return SwSuspendWait(duration_expr=arg)

        # channel.get() / channel.pop()
        if fn_name in ("get", "pop") and isinstance(fn, ir.ExprAttribute):
            fifo_field = _attr_base_name(fn.value)
            return SwSuspendFifoPop(fifo_field=fifo_field)

        # channel.put(v) / channel.push(v)
        if fn_name in ("put", "push") and isinstance(fn, ir.ExprAttribute):
            fifo_field = _attr_base_name(fn.value)
            val = inner.args[0] if inner.args else None
            return SwSuspendFifoPush(fifo_field=fifo_field, value_expr=val)

        # pool.lock()
        if fn_name == "lock" and isinstance(fn, ir.ExprAttribute):
            pool_field = _attr_base_name(fn.value)
            return SwSuspendMutex(pool_field=pool_field)

    return SwSuspendCall(call_expr=inner)


def _attr_base_name(expr: ir.Expr) -> Optional[str]:
    """Return the base name of an attribute chain, e.g. ``self.foo`` → ``foo``."""
    if isinstance(expr, ir.ExprAttribute):
        return expr.attr
    if isinstance(expr, (ir.ExprRefLocal, ir.ExprRefUnresolved)):
        return expr.name
    return None


def _split_at_awaits(stmts: list, comp_name: str, func_name: str) -> SwCoroutineFrame:
    """Split *stmts* at await points into a ``SwCoroutineFrame``.

    Liveness: variables assigned before any await and read after it are
    promoted to ``locals_struct``; variables entirely within one continuation
    remain as-is.
    """
    # -- collect top-level await positions ---------------------------------
    # We scan the top-level stmts list.  Awaits inside nested control flow
    # are collapsed: the entire stmt containing the await starts a new
    # continuation.  This is a conservative simplification consistent with the
    # existing DmAsyncMethodGenerator.

    segments: List[Tuple[list, Optional[ir.ExprAwait]]] = []
    current: list = []

    for stmt in stmts:
        awaits_in_stmt = _find_awaits(stmt)
        if awaits_in_stmt:
            # End current segment; each await in the stmt is its own break.
            for aw in awaits_in_stmt:
                current.append(stmt)
                segments.append((current, aw))
                current = []
                break  # one await per stmt boundary (simplification)
        else:
            current.append(stmt)

    segments.append((current, None))  # final continuation

    # -- liveness: detect variables crossing suspend points ----------------
    # For each segment, collect assigns and refs; if a name is assigned in
    # segment i and referenced in segment j > i, it must go into locals_struct.
    all_assigns: List[Set[str]] = [_assigns_in_stmts(s) for s, _ in segments]
    all_refs: List[Set[str]] = [_refs_in_stmts(s) for s, _ in segments]

    frame_vars: Set[str] = set()
    for i in range(len(segments) - 1):
        assigned_here = all_assigns[i]
        refs_later = set()
        for j in range(i + 1, len(segments)):
            refs_later |= all_refs[j]
        frame_vars |= assigned_here & refs_later

    # Build a mapping from local var name to DataType (from typed StmtAnnAssign nodes).
    type_hints: dict = {}
    for _, (seg_stmts, _) in enumerate(segments):
        for stmt in seg_stmts:
            if isinstance(stmt, ir.StmtAnnAssign):
                ir_type = getattr(stmt, 'ir_type', None)
                if ir_type is not None:
                    tgt = getattr(stmt, 'target', None)
                    if isinstance(tgt, ir.ExprRefLocal):
                        type_hints[tgt.name] = ir_type

    locals_struct = [SwLocalVar(var_name=n, var_type=type_hints.get(n)) for n in sorted(frame_vars)]

    # -- build continuations -----------------------------------------------
    continuations: List[SwContinuation] = []
    for idx, (seg_stmts, await_expr) in enumerate(segments):
        suspend = _classify_await(await_expr) if await_expr else None
        next_idx = idx + 1 if await_expr else None
        continuations.append(SwContinuation(
            index=idx,
            stmts=seg_stmts,
            suspend=suspend,
            next_index=next_idx,
        ))

    return SwCoroutineFrame(
        func_name=f"{comp_name}_{func_name}",
        comp_type_name=comp_name,
        locals_struct=locals_struct,
        continuations=continuations,
    )


# ---------------------------------------------------------------------------
# AsyncLowerPass
# ---------------------------------------------------------------------------

class AsyncLowerPass(SwPass):
    """Classify async functions; build SwCoroutineFrame for non-sync-convertible ones."""

    def run(self, ctxt: SwContext) -> SwContext:
        sync_map = _classify_all(ctxt)

        for type_name, dtype in ctxt.type_m.items():
            if not isinstance(dtype, (ir.DataTypeComponent, ir.DataTypeClass)):
                continue
            all_funcs = list(getattr(dtype, "functions", [])) + list(getattr(dtype, "proc_processes", []))
            for func in all_funcs:
                is_process = type(func).__name__ == "Process"
                is_promoted_process = (not is_process
                                       and getattr(func, "is_async", False)
                                       and getattr(func, "metadata", {}).get("is_process"))
                if not is_process and not getattr(func, "is_async", False):
                    continue
                key = f"{type_name}.{func.name}"
                # Promoted processes use sync_convertible only if they have no awaits
                if not is_process and not is_promoted_process and sync_map.get(key):
                    func.metadata["sync_convertible"] = True
                elif not is_process and is_promoted_process and sync_map.get(key):
                    func.metadata["sync_convertible"] = True
                else:
                    body = func.body if isinstance(func.body, list) else (func.body.stmts if func.body else [])
                    if body:
                        frame = _split_at_awaits(body, type_name, func.name)
                        # For promoted @process Functions with params, carry params in frame
                        if is_promoted_process and func.args and func.args.args:
                            frame.process_params = list(func.args.args)
                            frame.return_dtype = func.returns
                            # Add all params to locals_struct so they survive suspension
                            existing = {lv.var_name for lv in frame.locals_struct}
                            for arg in func.args.args:
                                if arg.arg not in existing:
                                    frame.locals_struct.insert(0, SwLocalVar(var_name=arg.arg))
                        ctxt.sw_nodes.setdefault(type_name, []).append(frame)

        return ctxt

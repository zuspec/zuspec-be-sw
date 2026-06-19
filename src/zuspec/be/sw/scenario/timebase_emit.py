"""Timebase-mode C emission — Layer-1 → ``zsp_timebase`` FSM coroutines.

Activated when a module contains any suspending construct (`ScWait` / `ScPar`).
In that case **every** coroutine is rendered as a `zsp_task_func`
(switch-on-`idx` state machine), and `main` drives the `zsp_timebase`
scheduler to quiescence. This is the Phase-5 counterpart to the plain
``__run`` functions the `CEmitter` emits for non-suspending (Phase 1–4) modules.

Coroutine task ABI (args via `va_list` at idx 0):
    (self_ptr, seed:uint64_t, par_block*, parent_thread*)

- A sequential `ScInvoke` → `zsp_timebase_call` (a block boundary; the callee
  runs on the same thread's stack, caller resumes in the next block).
- `ScPar` (ALL/NONE join) → spawn each branch as its own thread via
  `zsp_timebase_thread_create`, passing the shared `zsp_par_block` and the
  parent thread; each branch, on completion, does `done_one` + (if the join
  condition is met) `zsp_timebase_schedule(parent)`. The parent suspends
  (BLOCKED) after spawning and resumes when woken.
- `ScWait` → `zsp_timebase_wait` (fast-path falls through; slow-path suspends).

Loops/conditionals that *contain* a suspend (invoke/wait/par) are out of scope
here — `CoroutineFSMPass` rejects them (loop/branch-aware FSM is future work).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from zuspec.ir.core.scenario import (
    ScSolveProblem, ScExecBlock, ScSeq, ScAtomic, ScInvoke, ScPar, ScWait,
    ScImport,
)
from zuspec.ir.core.activity import JoinKind
from zuspec.ir.core.xf import CoroutineFSMPass
from .stmt_gen import ScenarioStmtGenerator, _Unsupported

_RT_INCLUDES = ["zsp_alloc.h", "zsp_timebase.h", "zsp_par_block.h"]
_END_TIME = "ZSP_TIME_NS(1000000000ULL)"   # run-to-quiescence upper bound


def module_uses_timebase(module) -> bool:
    return any(_contains_wait_or_par(c.body) for c in module.coroutines.values())


def _contains_wait_or_par(stmts) -> bool:
    for s in stmts:
        if isinstance(s, (ScWait, ScPar)):
            return True
        if isinstance(s, ScImport) and s.blocking:
            return True
        for attr in ("body", "then_body", "else_body"):
            sub = getattr(s, attr, None)
            if isinstance(sub, list) and _contains_wait_or_par(sub):
                return True
    return False


class TimebaseEmitter:
    def __init__(self, em, bridge: bool = False):
        self.em = em
        self.module = em.module
        # bridge=True: emit a host-driven dispatcher (`zsp_scenario_spawn`) and
        # no `main`, so the scenario links into a DPI shared object alongside
        # the zsp_bridge runtime. bridge=False: emit a standalone `main`.
        self.bridge = bridge
        # Per-module mode: every coroutine is a task, so every ScInvoke is a
        # timebase_call (a block boundary).
        self.blocking = set(self.module.coroutines)

    def export_action_ids(self):
        """Stable export-action → integer id map (shared with the SV shim)."""
        exports = self.module.export_actions or list(self.module.coroutines)
        return {name: i for i, name in enumerate(exports)
                if name in self.module.coroutines}

    # ------------------------------------------------------------------
    def emit(self) -> Tuple[str, str, str]:
        em = self.em
        coros = [self.module.coroutines[n] for n in self.module.coroutines]
        guard = "%s_H" % em.header.upper()
        solve_map = {c.name: em._solve_problem(c) for c in coros}
        uses_solver = any(p is not None for p in solve_map.values())

        # --- header: structs + randomize decls only (NO timebase / solver
        # runtime headers — their zsp_alloc.h's collide; each is pulled into
        # only the .c that needs it). Task decls live in the gen TU itself. ---
        h = ["#ifndef %s" % guard, "#define %s" % guard, "",
             "#include <stdint.h>", "#include <stdio.h>", "#include <string.h>",
             "", "extern uint64_t __zsp_seed_state;",
             "uint64_t zsp_next_seed(void);", ""]
        for c in coros:
            h.append(em._emit_struct(c))
            h.append("")
        for c in coros:
            if solve_map[c.name] is not None:
                h.append(em._randomize_decl(c))
        h += ["", "#endif /* %s */" % guard, ""]

        # --- gen source: tasks + LCG + main/dispatch (timebase runtime; NO
        # solver headers). ---
        s = ['#include "%s.h"' % em.header, '#include <stdlib.h>']
        for inc in _RT_INCLUDES:
            s.append('#include "%s"' % inc)
        if self.bridge:
            s.append('#include "zsp_bridge.h"')
        s += ["",
              "uint64_t __zsp_seed_state = 0;",
              "uint64_t zsp_next_seed(void) {",
              "    __zsp_seed_state = __zsp_seed_state * 6364136223846793005ULL"
              " + 1442695040888963407ULL;",
              "    return __zsp_seed_state;",
              "}",
              ""]
        for c in coros:
            s.append(self._emit_task(c))
            s.append("")
        s.extend(self._emit_dispatch() if self.bridge
                 else self._emit_main(uses_solver))

        # --- solve source: randomize only (solver headers; separate TU). ---
        solve = []
        if uses_solver:
            solve = ['#include "%s.h"' % em.header]
            for inc in ("zsp_problem.h", "zsp_block_alloc.h", "zsp_ctx.h",
                        "zsp_search.h"):
                solve.append('#include "%s"' % inc)
            solve.append("")
            for c in coros:
                if solve_map[c.name] is not None:
                    solve.append(em._emit_randomize(c))
                    solve.append("")

        return "\n".join(h), "\n".join(s), "\n".join(solve)

    def _emit_dispatch(self) -> List[str]:
        """Generic host driver hook: spawn a root coroutine by action id."""
        ids = self.export_action_ids()
        m = ["void zsp_scenario_spawn(zsp_timebase_t *tb, int action_id, "
             "uint64_t seed) {",
             "    __zsp_seed_state = seed;",
             "    switch (action_id) {"]
        for name, aid in ids.items():
            sn = self.em._struct_name(name)
            m += [
                "    case %d: {" % aid,
                "        %s *a = (%s *)calloc(1, sizeof(%s));" % (sn, sn, sn),
                "        zsp_timebase_thread_create(tb, &%s__task, "
                "ZSP_THREAD_FLAGS_NONE, a, zsp_next_seed(), (void *)0, "
                "(void *)0);" % name,
                "        break; }",
            ]
        m += ["    default: break;", "    }", "}", ""]
        return m

    # ------------------------------------------------------------------
    def _emit_task(self, coro) -> str:
        em = self.em
        dt = em._action_dt(coro)
        sn = em._struct_name(coro.name)
        sg = em._stmt_gen(dt)
        fsm = CoroutineFSMPass(blocking_targets=self.blocking).run(coro)

        # Assign frame slots for sub-structs / par-blocks used across suspends.
        slot_of: Dict[int, str] = {}
        decls: List[str] = []
        n = [0]
        for blk in fsm.blocks:
            sus = blk.suspend
            if isinstance(sus, ScInvoke):
                n[0] += 1
                name = "__sub%d" % n[0]
                slot_of[id(sus)] = name
                decls.append("%s %s;" % (em._struct_name(sus.target), name))
            elif isinstance(sus, ScPar):
                n[0] += 1
                pb = "__pb%d" % n[0]
                slot_of[id(sus)] = pb
                decls.append("zsp_par_block_t %s;" % pb)
                for j, br in enumerate(sus.branches):
                    if not isinstance(br, ScInvoke):
                        raise _Unsupported(
                            "parallel branch %d of %r must be a single traversal "
                            "(iteration 1)" % (j, coro.name))
                    bn = "%s_b%d" % (pb, j)
                    slot_of[id(br)] = bn
                    decls.append("%s %s;" % (em._struct_name(br.target), bn))
        has_import = any(isinstance(b.suspend, ScImport) for b in fsm.blocks)
        if has_import:
            decls.append("int __rid;")

        L = ["zsp_frame_t *%s__task(zsp_timebase_t *tb, zsp_thread_t *thread, "
             "int idx, va_list *args) {" % coro.name]
        L.append("    zsp_frame_t *ret = thread->leaf;")
        L.append("    typedef struct {")
        L.append("        %s *self;" % sn)
        L.append("        uint64_t seed;")
        L.append("        zsp_par_block_t *__pb;")
        L.append("        zsp_thread_t *__parent;")
        for d in decls:
            L.append("        " + d)
        L.append("    } locals_t;")
        L.append("    switch (idx) {")
        for i, blk in enumerate(fsm.blocks):
            L.append("    case %d: {" % i)
            L.append("        locals_t *locals = zsp_frame_locals(ret, locals_t);")
            if i == 0:
                # idx 0 also allocates the frame and extracts args.
                L[-1:] = [
                    "        ret = zsp_timebase_alloc_frame(thread, "
                    "sizeof(locals_t), &%s__task);" % coro.name,
                    "        locals_t *locals = zsp_frame_locals(ret, locals_t);",
                    "        if (args) {",
                    "            locals->self = (%s *)va_arg(*args, void *);" % sn,
                    "            locals->seed = va_arg(*args, uint64_t);",
                    "            locals->__pb = (zsp_par_block_t *)va_arg(*args, void *);",
                    "            locals->__parent = (zsp_thread_t *)va_arg(*args, void *);",
                    "        }",
                ]
            L.append("        %s *self = locals->self; (void)self;" % sn)
            L.append("        uint64_t seed = locals->seed; (void)seed;")
            # resume after a blocking import: release its request slot
            if i > 0 and isinstance(fsm.blocks[i - 1].suspend, ScImport):
                L.append("        zsp_scenario_import_done(locals->__rid);")
            # straight-line stmts
            L.extend(self._emit_block_stmts(coro, sg, blk.stmts))
            # block-ending suspend (or final return)
            L.extend(self._emit_suspend(coro, sg, blk, i, slot_of, len(fsm.blocks)))
            L.append("    }")
        L.append("    }")
        L.append("    return ret;")
        L.append("}")
        return "\n".join(L)

    def _emit_block_stmts(self, coro, sg, stmts) -> List[str]:
        out: List[str] = []
        for s in stmts:
            if isinstance(s, (ScSeq, ScAtomic)):
                out.extend(self._emit_block_stmts(coro, sg, s.body))
            elif isinstance(s, ScSolveProblem):
                out.append("        if (%s__randomize(self, seed) != 0) "
                           "{ ret = zsp_timebase_return(thread, 0); break; }"
                           % coro.name)
            elif isinstance(s, ScExecBlock):
                for st in s.stmts:
                    code = sg._gen_dm_stmt(st)
                    if code:
                        out.append("        " + code)
            else:
                raise _Unsupported(
                    "coroutine %r: %s is not supported in a timebase block "
                    "(iteration 1: blocks hold solve/exec only)"
                    % (coro.name, type(s).__name__))
        return out

    def _emit_suspend(self, coro, sg, blk, i, slot_of, n_blocks) -> List[str]:
        sus = blk.suspend
        nxt = i + 1
        if sus is None:
            # Final block: parallel-branch completion handshake, then return.
            return [
                "        if (locals->__pb) {",
                "            zsp_par_block_done_one(locals->__pb);",
                "            if (zsp_par_block_join(locals->__pb)) "
                "zsp_timebase_schedule(tb, locals->__parent);",
                "        }",
                "        ret = zsp_timebase_return(thread, 0); break;",
            ]
        if isinstance(sus, ScWait):
            t = sg._gen_dm_expr(sus.time)
            return [
                "        if (zsp_timebase_wait(thread, ZSP_TIME_NS(%s))) "
                "{ ret->idx = %d; break; }" % (t, nxt),
                "        /* fall through: time advanced without suspension */",
            ]
        if isinstance(sus, ScInvoke):
            sub = slot_of[id(sus)]
            return [
                "        memset(&locals->%s, 0, sizeof(locals->%s));" % (sub, sub),
                "        ret->idx = %d;" % nxt,
                "        ret = zsp_timebase_call(thread, &%s__task, "
                "&locals->%s, zsp_next_seed(), (void *)0, (void *)0); break;"
                % (sus.target, sub),
            ]
        if isinstance(sus, ScImport):
            argv = [sg._gen_dm_expr(a) for a in sus.args]
            args_c = "".join(", (int64_t)(%s)" % a for a in argv)
            return [
                "        ret->idx = %d;" % nxt,
                "        locals->__rid = zsp_scenario_post_import(thread, %d, %d%s);"
                % (sus.fn_id, len(argv), args_c),
                "        break;",
            ]
        if isinstance(sus, ScPar):
            return self._emit_par(coro, sus, i, slot_of)
        raise _Unsupported("coroutine %r: unsupported suspend %s"
                           % (coro.name, type(sus).__name__))

    def _emit_par(self, coro, par, i, slot_of) -> List[str]:
        pb = slot_of[id(par)]
        nxt = i + 1
        join_all = True
        if par.join_spec is not None and par.join_spec.kind == JoinKind.NONE:
            join_all = False
        out = ["        zsp_par_block_init(&locals->%s, %d);"
               % (pb, len(par.branches))]
        for br in par.branches:
            bn = slot_of[id(br)]
            out.append("        memset(&locals->%s, 0, sizeof(locals->%s));"
                       % (bn, bn))
            out.append("        zsp_timebase_thread_create(tb, &%s__task, "
                       "ZSP_THREAD_FLAGS_NONE, &locals->%s, zsp_next_seed(), "
                       "&locals->%s, thread);" % (br.target, bn, pb))
        out.append("        ret->idx = %d;" % nxt)
        if join_all:
            out.append("        thread->flags |= ZSP_THREAD_FLAGS_BLOCKED; break;")
        else:
            # NONE join: don't wait — fall through to the continuation.
            out.append("        /* join=NONE: continue without waiting */")
        return out

    # ------------------------------------------------------------------
    def _emit_main(self, uses_solver) -> List[str]:
        exports = self.module.export_actions or list(self.module.coroutines)
        m = ["int main(int argc, char **argv) {",
             "    uint64_t __seed = (argc > 1) ? strtoull(argv[1], 0, 0) : 1ULL;",
             "    int __iters = (argc > 2) ? atoi(argv[2]) : 1;"]
        m += [
            "    __zsp_seed_state = __seed;",
            "    zsp_alloc_t __alloc; zsp_alloc_malloc_init(&__alloc);",
            "    for (int __i = 0; __i < __iters; __i++) {",
            "        zsp_timebase_t __tb;",
            "        zsp_timebase_init(&__tb, &__alloc, ZSP_TIME_NS);",
        ]
        for name in exports:
            if name not in self.module.coroutines:
                continue
            sn = self.em._struct_name(name)
            m += [
                "        %s __a%s; memset(&__a%s, 0, sizeof(__a%s));"
                % (sn, name, name, name),
                "        zsp_timebase_thread_create(&__tb, &%s__task, "
                "ZSP_THREAD_FLAGS_NONE, &__a%s, zsp_next_seed(), (void *)0, "
                "(void *)0);" % (name, name),
            ]
        m += [
            "        zsp_timebase_run_until(&__tb, %s);" % _END_TIME,
            "        zsp_timebase_destroy(&__tb);",
            "    }",
            "    return 0;",
            "}",
            "",
        ]
        return m

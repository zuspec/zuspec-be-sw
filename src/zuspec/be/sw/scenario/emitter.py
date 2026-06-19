"""Layer-1 (``scenario`` dialect) → C emitter — Phase-2 atomic slice.

Emits, for a :class:`~zuspec.ir.core.ScenarioModule`, a self-contained C program:
an action struct per lowered coroutine, a body function per coroutine, and a
``main()`` that runs each exported action's (Phase-2) lifecycle — for now just
its body, with rand fields zero-initialized (constraint solving is Phase 3).

The atomic slice has no suspend points, so each :class:`ScCoroutine` becomes a
plain C function (the ``CoroutineFSMPass`` no-suspend path, impl-plan C3).  It
depends only on ``<stdio.h>``/``<stdint.h>``/``<string.h>`` — no ``zsp_*``
runtime — keeping the walking skeleton minimal.  Concurrency/timebase wiring
arrives with Phases 4–5.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from zuspec.be.sw.type_mapper import TypeMapper
from zuspec.ir.core.scenario import (
    ScSolveProblem, ScExecBlock, ScSeq, ScInvoke, ScLoop, ScIf, ScMatch,
    ScAtomic, ScSelect, ScPar, ScWait,
)
from .stmt_gen import ScenarioStmtGenerator, _Unsupported
from .constraint_c import ConstraintCEmitter

# Static buffer sizes for the per-call solve (iteration 1: generous & fixed).
_PROB_BUF = 1 << 16   # 64 KiB problem pool
_CTX_BUF = 1 << 20    # 1 MiB solver static segment
_BLOCK_SZ = 1 << 20   # 1 MiB block-allocator block

_SOLVER_INCLUDES = [
    "zsp_problem.h", "zsp_block_alloc.h", "zsp_ctx.h", "zsp_search.h",
]


def _type_map(ctx: Any) -> Dict[str, Any]:
    if isinstance(ctx, dict):
        return ctx
    for attr in ("type_map", "type_m"):
        tm = getattr(ctx, attr, None)
        if isinstance(tm, dict):
            return tm
    raise TypeError("no type map on %r" % type(ctx).__name__)


class CEmitter:
    """Render a :class:`ScenarioModule` to C source text.

    Args:
        module: The Layer-1 module to render.
        ctx:    The originating Layer-0 container (for action field/type lookup).
        header: Base name (no extension) for the emitted files.
    """

    def __init__(self, module, ctx, header: str = "scenario_gen",
                 bridge: bool = False):
        self.module = module
        self.ctx = ctx
        self.type_map = _type_map(ctx)
        self.type_mapper = TypeMapper()
        self.header = header
        # bridge=True: emit a generic zsp_scenario_spawn dispatcher (+ no main)
        # for the DPI shared library, in whichever mode the module needs.
        self.bridge = bridge

    def export_action_ids(self):
        exports = self.module.export_actions or list(self.module.coroutines)
        return {name: i for i, name in enumerate(exports)
                if name in self.module.coroutines}

    def solve_imports(self):
        """name → fn_id for non-blocking (solve) imports (rendered inline)."""
        return {d.name: d.fn_id for d in getattr(self.module, "imports", [])
                if not d.blocking}

    def _stmt_gen(self, dt):
        return ScenarioStmtGenerator(component=dt, ctxt=self.ctx,
                                     solve_imports=self.solve_imports())

    # ------------------------------------------------------------------
    def _action_dt(self, coro):
        if coro.action_type is None or coro.action_type not in self.type_map:
            raise _Unsupported(
                "coroutine %r has no resolvable action type" % coro.name)
        return self.type_map[coro.action_type]

    def _struct_name(self, name: str) -> str:
        return "%s_t" % name

    def _emit_struct(self, coro) -> str:
        dt = self._action_dt(coro)
        lines = ["typedef struct %s_s {" % coro.name]
        for f in dt.fields:
            ctype = self.type_mapper.map_type(f.datatype)
            lines.append("    %s %s;" % (ctype, f.name))
        if not dt.fields:
            lines.append("    int _empty;  /* no fields */")
        lines.append("} %s;" % self._struct_name(coro.name))
        return "\n".join(lines)

    def _run_decl(self, coro) -> str:
        return "void %s__run(%s *self, uint64_t seed);" % (
            coro.name, self._struct_name(coro.name))

    def _emit_run_fn(self, coro) -> str:
        """Emit the whole-lifecycle function for a coroutine.

        Non-suspending (Phase 4): a plain C function that runs solve → body /
        activity in order.  ``ScInvoke`` instantiates a fresh sub-action and
        recurses via its ``__run``.  (FSM switch-on-idx rendering for genuinely
        suspending coroutines — ``ScWait`` / ``ScPar`` — is Phase 5.)
        """
        # Guard: the non-suspending path only applies when CoroutineFSMPass
        # finds a single block.  A suspending coroutine (ScWait/ScPar/blocking
        # invoke) needs FSM switch-on-idx rendering — Phase 5.
        from zuspec.ir.core.xf import CoroutineFSMPass
        fsm = CoroutineFSMPass().run(coro)
        if fsm.suspends:
            raise _Unsupported(
                "coroutine %r suspends (%d blocks); FSM C rendering is Phase 5"
                % (coro.name, fsm.n_blocks))

        dt = self._action_dt(coro)
        sg = self._stmt_gen(dt)
        ctr = [0]   # sub-instance / loop-var counter (mutable across recursion)
        has_solve = self._solve_problem(coro) is not None
        out = ["void %s__run(%s *self, uint64_t seed) {"
               % (coro.name, self._struct_name(coro.name))]
        if not has_solve:
            out.append("    (void)seed;")
        out.extend(self._emit_stmts(coro, sg, coro.body, 1, ctr))
        out.append("}")
        return "\n".join(out)

    def _emit_stmts(self, coro, sg, stmts, depth, ctr) -> List[str]:
        pad = "    " * depth
        out: List[str] = []
        for s in stmts:
            if isinstance(s, ScSolveProblem):
                out.append(pad + "if (%s__randomize(self, seed) != 0) return;"
                           % coro.name)
            elif isinstance(s, ScExecBlock):
                for st in s.stmts:
                    code = sg._gen_dm_stmt(st)
                    if code:
                        out.append(pad + code)
            elif isinstance(s, (ScSeq, ScAtomic)):
                out.extend(self._emit_stmts(coro, sg, s.body, depth, ctr))
            elif isinstance(s, ScInvoke):
                ctr[0] += 1
                var = "__sub%d" % ctr[0]
                tn = self._struct_name(s.target)
                out.append(pad + "{ %s %s; memset(&%s, 0, sizeof(%s));"
                           % (tn, var, var, var))
                out.append(pad + "  %s__run(&%s, zsp_next_seed()); }"
                           % (s.target, var))
            elif isinstance(s, ScLoop):
                out.extend(self._emit_loop(coro, sg, s, depth, ctr))
            elif isinstance(s, ScIf):
                cond = sg._gen_dm_expr(s.cond)
                out.append(pad + "if (%s) {" % cond)
                out.extend(self._emit_stmts(coro, sg, s.then_body, depth + 1, ctr))
                if s.else_body:
                    out.append(pad + "} else {")
                    out.extend(self._emit_stmts(coro, sg, s.else_body, depth + 1, ctr))
                out.append(pad + "}")
            elif isinstance(s, ScMatch):
                out.extend(self._emit_match(coro, sg, s, depth, ctr))
            elif isinstance(s, ScSelect):
                out.extend(self._emit_select(coro, sg, s, depth, ctr))
            else:
                raise _Unsupported(
                    "coroutine %r: cannot emit %s in a non-suspending body "
                    "(Phase 5?)" % (coro.name, type(s).__name__))
        return out

    @staticmethod
    def _const_weight(sg, w) -> int:
        from zuspec.ir.core.expr import ExprConstant
        if w is None:
            return 1
        if isinstance(w, ExprConstant) and isinstance(w.value, int):
            return max(1, int(w.value))
        raise _Unsupported("select branch weights must be constant integers "
                           "in iteration 1")

    def _emit_select(self, coro, sg, s, depth, ctr) -> List[str]:
        """Weighted single choice via the root LCG (synchronous; no timebase)."""
        pad = "    " * depth
        weights = [self._const_weight(sg, b.weight) for b in s.branches]
        total = sum(weights)
        ctr[0] += 1
        rv = "__sel%d" % ctr[0]
        out = [pad + "{ uint64_t %s = zsp_next_seed() %% %d;" % (rv, total)]
        acc = 0
        for i, (b, w) in enumerate(zip(s.branches, weights)):
            acc += w
            kw = "if" if i == 0 else "} else if"
            out.append(pad + "  %s (%s < %d) {" % (kw, rv, acc))
            out.extend(self._emit_stmts(coro, sg, b.body, depth + 2, ctr))
        out.append(pad + "  } }")
        return out

    def _emit_loop(self, coro, sg, s, depth, ctr) -> List[str]:
        pad = "    " * depth
        if s.kind != "repeat" or s.count is None:
            raise _Unsupported(
                "coroutine %r: only counted `repeat` loops are supported in "
                "Phase 4 (got kind=%r)" % (coro.name, s.kind))
        ctr[0] += 1
        iv = s.index_var or "__i%d" % ctr[0]
        count = sg._gen_dm_expr(s.count)
        out = [pad + "for (int %s = 0; %s < (int)(%s); %s++) {"
               % (iv, iv, count, iv)]
        out.extend(self._emit_stmts(coro, sg, s.body, depth + 1, ctr))
        out.append(pad + "}")
        return out

    def _emit_match(self, coro, sg, s, depth, ctr) -> List[str]:
        pad = "    " * depth
        subject = sg._gen_dm_expr(s.subject)
        out: List[str] = []
        first = True
        default = None
        for case in s.cases:
            if case.pattern is None:
                default = case
                continue
            pat = sg._gen_dm_expr(case.pattern)
            kw = "if" if first else "} else if"
            first = False
            out.append(pad + "%s ((%s) == (%s)) {" % (kw, subject, pat))
            out.extend(self._emit_stmts(coro, sg, case.body, depth + 1, ctr))
        if default is not None:
            out.append(pad + ("} else {" if not first else "{"))
            out.extend(self._emit_stmts(coro, sg, default.body, depth + 1, ctr))
        if not first or default is not None:
            out.append(pad + "}")
        return out

    # --- solve problem -------------------------------------------------
    @staticmethod
    def _solve_problem(coro):
        for blk in coro.body:
            if isinstance(blk, ScSolveProblem):
                return blk
        return None

    @staticmethod
    def _var_bounds(width: int, signed: bool) -> Tuple[int, int]:
        if signed:
            return -(1 << (width - 1)), (1 << (width - 1)) - 1
        if width >= 64:
            return 0, (1 << 63) - 1   # clamp: lo/hi are int64 in the C API
        return 0, (1 << width) - 1

    def _randomize_decl(self, coro) -> str:
        return ("int %s__randomize(%s *self, uint64_t seed);"
                % (coro.name, self._struct_name(coro.name)))

    def _emit_randomize(self, coro) -> str:
        sp = self._solve_problem(coro)
        dt = self._action_dt(coro)
        fields = {f.name: f for f in dt.fields}
        sn = self._struct_name(coro.name)
        L = ["int %s__randomize(%s *self, uint64_t seed) {" % (coro.name, sn)]
        L.append("    static uint8_t __prob_buf[%d];" % _PROB_BUF)
        L.append("    static uint8_t __ctx_buf[%d];" % _CTX_BUF)
        L.append("    SolveProblem *sp = solve_problem_init(__prob_buf, sizeof(__prob_buf));")
        for v in sp.vars:
            lo, hi = self._var_bounds(v.width, v.signed)
            L.append("    problem_add_var(sp, %d, %d, %d, %dLL, %dLL);"
                     % (v.var_id, v.width, 1 if v.signed else 0, lo, hi))
        # constraints
        cc = ConstraintCEmitter({v.name: v.var_id for v in sp.vars}, sp="sp")
        for c in sp.constraints:
            cc.emit_constraint(c)
        for line in cc.lines:
            L.append("    " + line)
        # solve
        L += [
            "    zsp_block_alloc_t *__ba = zsp_block_alloc_create(NULL, %d);" % _BLOCK_SZ,
            "    SolveCtx *__ctx = solver_create(__ctx_buf, sizeof(__ctx_buf), __ba);",
            "    if (solver_compile(__ctx, sp) != 0) {",
            '        fprintf(stderr, "%s__randomize: compile failed\\n");' % coro.name,
            "        solver_destroy(__ctx); zsp_block_alloc_destroy(__ba); return 1;",
            "    }",
            "    SolveOpts __opts; memset(&__opts, 0, sizeof(__opts)); __opts.seed = seed;",
            "    SolveResult __r = solver_solve(__ctx, &__opts);",
            "    if (__r != SOLVE_OK) {",
            '        fprintf(stderr, "%s__randomize: solve failed (%%d)\\n", __r);' % coro.name,
            "        solver_destroy(__ctx); zsp_block_alloc_destroy(__ba); return 1;",
            "    }",
        ]
        for name, vid in sp.writeback.items():
            ctype = self.type_mapper.map_type(fields[name].datatype)
            L.append("    self->%s = (%s)solver_get_value(__ctx, %d);" % (name, ctype, vid))
        L += [
            "    solver_destroy(__ctx); zsp_block_alloc_destroy(__ba);",
            "    return 0;",
            "}",
        ]
        return "\n".join(L)

    # ------------------------------------------------------------------
    def emit(self) -> Tuple[str, str, str]:
        """Return ``(header_text, source_text, main_text)``."""
        from .timebase_emit import module_uses_timebase, TimebaseEmitter
        if module_uses_timebase(self.module):
            return TimebaseEmitter(self, bridge=self.bridge).emit()

        coros = [self.module.coroutines[n] for n in self.module.coroutines]

        # --- header ---
        guard = "%s_H" % self.header.upper()
        solve_map = {c.name: self._solve_problem(c) for c in coros}
        uses_solver = any(p is not None for p in solve_map.values())

        # Header stays free of the dv-solve and timebase runtime headers (their
        # zsp_alloc.h's collide); each is pulled into only the .c that needs it.
        h = ["#ifndef %s" % guard, "#define %s" % guard, "",
             "#include <stdint.h>", "#include <stdio.h>", "#include <string.h>", ""]
        # Shared root LCG (single definition in the source; a top seed
        # reproduces a whole run). Declared here so __run functions in the
        # source TU and main() in main.c share one state.
        h += [
            "extern uint64_t __zsp_seed_state;",
            "uint64_t zsp_next_seed(void);",
            "",
        ]
        for c in coros:
            h.append(self._emit_struct(c))
            h.append("")
        for c in coros:
            h.append(self._run_decl(c))
            if solve_map[c.name] is not None:
                h.append(self._randomize_decl(c))
        h += ["", "#endif /* %s */" % guard, ""]

        # --- gen source (runs + LCG + main/dispatch; NO solver headers) ---
        s = ['#include "%s.h"' % self.header,
             '#include <stdlib.h>']
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
            s.append(self._emit_run_fn(c))
            s.append("")
        if self.bridge:
            s.extend(self._emit_plain_dispatch())
        else:
            s.extend(self._emit_plain_main())

        # --- solve source (randomize only; solver headers; separate TU so the
        # dv-solve / timebase zsp_alloc.h's never co-occur) ---
        solve = []
        if uses_solver:
            solve = ['#include "%s.h"' % self.header]
            for inc in _SOLVER_INCLUDES:
                solve.append('#include "%s"' % inc)
            solve.append("")
            for c in coros:
                if solve_map[c.name] is not None:
                    solve.append(self._emit_randomize(c))
                    solve.append("")

        return "\n".join(h), "\n".join(s), "\n".join(solve)

    def _emit_plain_main(self) -> List[str]:
        exports = self.module.export_actions or list(self.module.coroutines)
        m = ["int main(int argc, char **argv) {",
             "    uint64_t __seed = (argc > 1) ? strtoull(argv[1], 0, 0) : 1ULL;",
             "    int __iters = (argc > 2) ? atoi(argv[2]) : 1;",
             "    __zsp_seed_state = __seed;",
             "    for (int __i = 0; __i < __iters; __i++) {"]
        for name in exports:
            if name not in self.module.coroutines:
                continue
            sn = self._struct_name(name)
            m += ["        {", "            %s a;" % sn,
                  "            memset(&a, 0, sizeof(a));",
                  "            %s__run(&a, zsp_next_seed());" % name, "        }"]
        m += ["    }", "    return 0;", "}", ""]
        return m

    def _emit_plain_dispatch(self) -> List[str]:
        """Bridge dispatcher for a non-suspending (plain) module: the export's
        whole lifecycle is a synchronous C call — no timebase needed."""
        m = ["void zsp_scenario_spawn(zsp_timebase_t *tb, int action_id, "
             "uint64_t seed) {",
             "    (void)tb;",
             "    __zsp_seed_state = seed;",
             "    switch (action_id) {"]
        for name, aid in self.export_action_ids().items():
            sn = self._struct_name(name)
            m += [
                "    case %d: {" % aid,
                "        %s a; memset(&a, 0, sizeof(a));" % sn,
                "        %s__run(&a, zsp_next_seed());" % name,
                "        break; }",
            ]
        m += ["    default: break;", "    }", "}", ""]
        return m

    def write(self, output_dir) -> List[Path]:
        """Emit the files into *output_dir*; return the list of source paths to
        compile (the ``.c`` files; the header is included, not compiled)."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        header_text, gen_text, solve_text = self.emit()
        (out / ("%s.h" % self.header)).write_text(header_text)
        cp = out / ("%s.c" % self.header)
        cp.write_text(gen_text)
        sources = [cp]
        if solve_text.strip():
            sp = out / "scenario_solve.c"
            sp.write_text(solve_text)
            sources.append(sp)
        return sources

"""Phase-3b(a): blocking subtask calls -- one task awaits another task.

Exercises cross-method coroutine composition on the timebase ABI:
  - a void subtask call: run() awaits step() twice; each step consumes time
    (proves caller-frame resume idx + zsp_timebase_call trampoline + nested
    suspend inside the callee)
  - a value-returning subtask call: run2() does `self.acc = await compute(21)`
    (proves the result returns via thread->rval and lands in the resume block)

fe-sv mapping is later; the IR is built directly and pins the task-call shape.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from zuspec.dataclasses import ir
from zuspec.be.sw import class_codegen

_HERE = Path(__file__).parent
_SHARE = _HERE.parent.parent / "src" / "zuspec" / "be" / "sw" / "share"
_INCLUDE = _SHARE / "include"
_RT = _SHARE / "rt"


def _find_cc():
    for cc in ("gcc", "clang", "cc"):
        if shutil.which(cc):
            return cc
    return None


def _S():
    return ir.TypeExprRefSelf()


def _F(a):
    return ir.ExprAttribute(value=_S(), attr=a)


def _I():
    return ir.DataTypeInt(bits=32, signed=True)


def _wait(n):
    return ir.StmtExpr(expr=ir.ExprCall(
        func=ir.ExprAttribute(value=_S(), attr="wait"),
        args=[ir.ExprConstant(value=n)]))


def _await_call(m, *a):
    return ir.ExprAwait(value=ir.ExprCall(
        func=ir.ExprAttribute(value=_S(), attr=m), args=list(a)))


def _build_context():
    """class worker;
           int acc;
           function new();          // acc = 0
           task step(int n);        // acc += n; #2ns
           task run();              // await step(5); await step(7)
           task compute(int a);     // #1ns; return a + a
           task run2();             // acc = await compute(21)
       endclass
    """
    w = ir.DataTypeClass(name="worker", super=None)
    w.fields = [ir.Field(name="acc", datatype=_I())]

    new = ir.Function(
        name="new", args=ir.Arguments(args=[]), returns=None,
        body=[ir.StmtAssign(targets=[_F("acc")], value=ir.ExprConstant(value=0))])

    step = ir.Function(
        name="step", is_async=True,
        args=ir.Arguments(args=[ir.Arg(arg="n")]), returns=None,
        body=[
            ir.StmtAssign(targets=[_F("acc")], value=ir.ExprBin(
                lhs=_F("acc"), op=ir.BinOp.Add, rhs=ir.ExprRefParam(name="n"))),
            _wait(2),
        ])

    run = ir.Function(
        name="run", is_async=True, args=ir.Arguments(args=[]), returns=None,
        body=[
            ir.StmtExpr(expr=_await_call("step", ir.ExprConstant(value=5))),
            ir.StmtExpr(expr=_await_call("step", ir.ExprConstant(value=7))),
        ])

    compute = ir.Function(
        name="compute", is_async=True,
        args=ir.Arguments(args=[ir.Arg(arg="a")]), returns=_I(),
        body=[
            _wait(1),
            ir.StmtReturn(value=ir.ExprBin(
                lhs=ir.ExprRefParam(name="a"), op=ir.BinOp.Add,
                rhs=ir.ExprRefParam(name="a"))),
        ])

    run2 = ir.Function(
        name="run2", is_async=True, args=ir.Arguments(args=[]), returns=None,
        body=[ir.StmtAssign(targets=[_F("acc")],
                            value=_await_call("compute", ir.ExprConstant(value=21)))])

    w.functions = [new, step, run, compute, run2]
    return ir.Context(type_m={"worker": w})


_HARNESS = r"""
#include <assert.h>
#include <stdio.h>
#include "model.h"

zsp_alloc_t *zsp_default_alloc = 0;

int main(void) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);
    zsp_default_alloc = &alloc;

    /* --- void subtask calls: run() awaits step(5), step(7) --- */
    {
        zsp_timebase_t tb;
        zsp_timebase_init(&tb, &alloc, ZSP_TIME_PS);
        worker_t *w = ZSP_NEW(worker_t, &alloc, worker_type);
        worker__new(w);
        zsp_timebase_thread_create(&tb, &worker__run_task,
                                   ZSP_THREAD_FLAGS_NONE, (void *)w);
        zsp_timebase_run_until(&tb, ZSP_TIME_NS(1000));
        assert(w->acc == 12);                       /* 5 + 7 */
        assert(zsp_timebase_current_ticks(&tb) >= 4000);  /* two #2ns waits */
        zsp_object_decref((zsp_object_t *)w);
        zsp_object_free(&alloc, (zsp_object_t *)w);
    }

    /* --- value-returning subtask: run2() sets acc = compute(21) --- */
    {
        zsp_timebase_t tb;
        zsp_timebase_init(&tb, &alloc, ZSP_TIME_PS);
        worker_t *w = ZSP_NEW(worker_t, &alloc, worker_type);
        worker__new(w);
        zsp_timebase_thread_create(&tb, &worker__run2_task,
                                   ZSP_THREAD_FLAGS_NONE, (void *)w);
        zsp_timebase_run_until(&tb, ZSP_TIME_NS(1000));
        assert(w->acc == 42);                       /* 21 + 21 */
        assert(zsp_timebase_current_ticks(&tb) >= 1000);  /* #1ns inside compute */
        zsp_object_decref((zsp_object_t *)w);
        zsp_object_free(&alloc, (zsp_object_t *)w);
    }

    printf("class_subtask_slice: OK\n");
    return 0;
}
"""


@pytest.mark.skipif(_find_cc() is None, reason="no C compiler available")
def test_class_subtask_slice(tmp_path):
    cc = _find_cc()
    ctxt = _build_context()

    hp, cp = class_codegen.generate_class(ctxt, tmp_path, basename="model")
    (tmp_path / "harness.c").write_text(_HARNESS)

    exe = tmp_path / "subtask_slice"
    cmd = [
        cc, "-g", "-O0", "-Wall",
        f"-I{_INCLUDE}", f"-I{tmp_path}",
        str(cp), str(tmp_path / "harness.c"),
        str(_RT / "zsp_object.c"), str(_RT / "zsp_alloc.c"),
        str(_RT / "zsp_timebase.c"),
        "-o", str(exe),
    ]
    comp = subprocess.run(cmd, capture_output=True, text=True)
    assert comp.returncode == 0, (
        "compile failed:\n" + comp.stderr +
        "\n--- generated source ---\n" + Path(cp).read_text()
    )

    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0, f"run failed:\n{run.stdout}\n{run.stderr}"
    assert "class_subtask_slice: OK" in run.stdout

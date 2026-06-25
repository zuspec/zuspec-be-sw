"""Phase-3b slice: a class `task` (async method) -> C coroutine on the timebase.

Proves the blocking / time-consuming half of the class model:
  - an async method lowers to a switch/case coroutine (zsp_task_func ABI)
  - the body splits at a suspend point (`await self.wait(t)`)
  - persistent state (self) survives the suspend via the frame `locals` struct
  - the timebase scheduler resumes the coroutine after time advances

fe-sv mapping is a later phase, so the IR is built directly; this also pins the
task IR shape the front end must produce.
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


def _self():
    return ir.TypeExprRefSelf()


def _field(a):
    return ir.ExprAttribute(value=_self(), attr=a)


def _int(bits=32, signed=True):
    return ir.DataTypeInt(bits=bits, signed=signed)


def _build_context():
    """class ticker;
           int x;
           function new();        // self.x = 0
           task run();            // x=1; #5ns; x=x+10
       endclass
    """
    t = ir.DataTypeClass(name="ticker", super=None)
    t.fields = [ir.Field(name="x", datatype=_int())]

    new = ir.Function(
        name="new", args=ir.Arguments(args=[]), returns=None,
        body=[ir.StmtAssign(targets=[_field("x")],
                            value=ir.ExprConstant(value=0))])

    run = ir.Function(
        name="run", is_async=True, args=ir.Arguments(args=[]), returns=None,
        body=[
            ir.StmtAssign(targets=[_field("x")], value=ir.ExprConstant(value=1)),
            # suspend point: await self.wait(5ns)
            ir.StmtExpr(expr=ir.ExprCall(
                func=ir.ExprAttribute(value=_self(), attr="wait"),
                args=[ir.ExprConstant(value=5)])),
            ir.StmtAssign(targets=[_field("x")], value=ir.ExprBin(
                lhs=_field("x"), op=ir.BinOp.Add, rhs=ir.ExprConstant(value=10))),
        ])
    t.functions = [new, run]
    return ir.Context(type_m={"ticker": t})


_HARNESS = r"""
#include <assert.h>
#include <stdio.h>
#include "model.h"

zsp_alloc_t *zsp_default_alloc = 0;

int main(void) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);
    zsp_default_alloc = &alloc;

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_PS);

    ticker_t *t = ZSP_NEW(ticker_t, &alloc, ticker_type);
    ticker__new(t);
    assert(t->x == 0);

    /* launch the task: self is passed through to idx==0 via varargs */
    zsp_timebase_thread_create(&tb, &ticker__run_task,
                               ZSP_THREAD_FLAGS_NONE, (void *)t);

    /* before any time advance, only the first block has run (x=1),
       then the task suspended on #5ns */
    assert(t->x == 1);
    assert(zsp_timebase_current_ticks(&tb) == 0);

    /* drive the scheduler: time advances to 5ns, task resumes -> x = 11 */
    zsp_timebase_run_until(&tb, ZSP_TIME_NS(1000));
    assert(t->x == 11);
    /* time advanced by the #5ns wait (5ns == 5000ps) */
    assert(zsp_timebase_current_ticks(&tb) >= 5000);

    zsp_object_decref((zsp_object_t *)t);
    zsp_object_free(&alloc, (zsp_object_t *)t);

    printf("class_task_slice: OK\n");
    return 0;
}
"""


@pytest.mark.skipif(_find_cc() is None, reason="no C compiler available")
def test_class_task_slice(tmp_path):
    cc = _find_cc()
    ctxt = _build_context()

    hp, cp = class_codegen.generate_class(ctxt, tmp_path, basename="model")
    (tmp_path / "harness.c").write_text(_HARNESS)

    exe = tmp_path / "task_slice"
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
    assert "class_task_slice: OK" in run.stdout

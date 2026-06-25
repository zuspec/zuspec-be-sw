"""Phase-5 milestone slice: hand-built class IR -> C -> compile -> run.

Exercises every risky seam of the class-model lowering at minimum size:
  - base + derived with prefix-layout single inheritance
  - a virtual method, overridden in the derived class
  - `super.f()` lowered as a direct (non-virtual) call
  - a non-virtual constructor with constructor chaining (super.new)
  - `obj = new T(...)` (ExprNew) in method context via the allocator seam
  - a managed-handle field with a precise GC root map + refcount teardown

fe-sv mapping is a later phase, so the IR is constructed directly here; this
test also pins the IR *shape* the front end must eventually produce.
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


def _int(bits=32, signed=True):
    return ir.DataTypeInt(bits=bits, signed=signed)


def _self():
    return ir.TypeExprRefSelf()


def _field(self_attr):
    return ir.ExprAttribute(value=_self(), attr=self_attr)


def _build_context():
    """Build:

        class base;
            int x;
            function new(int x);    // ctor: self.x = x
            virtual function int f();   // return self.x
        endclass

        class derived extends base;
            int   y;
            base  child;            // managed handle
            function new(int x, int y); // super.new(x); self.y=y; self.child=null
            virtual function int f();   // return super.f() + self.y
            function void spawn();      // self.child = new base(99)
        endclass
    """
    # ---- base ----
    base = ir.DataTypeClass(name="base", super=None)
    base.fields = [ir.Field(name="x", datatype=_int())]

    base_new = ir.Function(
        name="new",
        args=ir.Arguments(args=[ir.Arg(arg="x")]),
        returns=None,
        body=[ir.StmtAssign(
            targets=[_field("x")],
            value=ir.ExprRefParam(name="x"))],
    )
    base_f = ir.Function(
        name="f",
        args=ir.Arguments(args=[]),
        returns=_int(),
        metadata={"virtual": True},
        body=[ir.StmtReturn(value=_field("x"))],
    )
    base.functions = [base_new, base_f]

    # ---- derived ----
    derived = ir.DataTypeClass(name="derived", super=base)
    derived.fields = [
        ir.Field(name="y", datatype=_int()),
        ir.Field(name="child", datatype=base),   # handle => GC root
    ]

    super_ref = ir.ExprRefUnresolved(name="super")
    derived_new = ir.Function(
        name="new",
        args=ir.Arguments(args=[ir.Arg(arg="x"), ir.Arg(arg="y")]),
        returns=None,
        body=[
            ir.StmtExpr(expr=ir.ExprCall(
                func=ir.ExprAttribute(value=super_ref, attr="new"),
                args=[ir.ExprRefParam(name="x")])),
            ir.StmtAssign(targets=[_field("y")],
                          value=ir.ExprRefParam(name="y")),
            ir.StmtAssign(targets=[_field("child")],
                          value=ir.ExprConstant(value=0)),
        ],
    )
    derived_f = ir.Function(
        name="f",
        args=ir.Arguments(args=[]),
        returns=_int(),
        metadata={"virtual": True},
        body=[ir.StmtReturn(value=ir.ExprBin(
            lhs=ir.ExprCall(
                func=ir.ExprAttribute(value=super_ref, attr="f"), args=[]),
            op=ir.BinOp.Add,
            rhs=_field("y")))],
    )
    derived_spawn = ir.Function(
        name="spawn",
        args=ir.Arguments(args=[]),
        returns=None,
        body=[ir.StmtAssign(
            targets=[_field("child")],
            value=ir.ExprNew(datatype=base, args=[ir.ExprConstant(value=99)]))],
    )
    derived.functions = [derived_new, derived_f, derived_spawn]

    return ir.Context(type_m={"base": base, "derived": derived})


_HARNESS = r"""
#include <assert.h>
#include <stdio.h>
#include "model.h"

/* define the allocation seam the generated `new` references */
zsp_alloc_t *zsp_default_alloc = 0;

int main(void) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);
    zsp_default_alloc = &alloc;

    /* base b = new base(10); */
    base_t *b = ZSP_NEW(base_t, &alloc, base_type);
    base__new(b, 10);
    assert(ZSP_VCALL(base_type_t, f, b) == 10);

    /* derived d = new derived(3, 4); */
    derived_t *d = ZSP_NEW(derived_t, &alloc, derived_type);
    derived__new(d, 3, 4);

    /* virtual dispatch picks the override: super.f()+y == 3+4 */
    assert(ZSP_VCALL(base_type_t, f, (base_t *)d) == 7);

    /* GC root map emitted for derived's managed handle */
    {
        zsp_object_type_t *dt = (zsp_object_type_t *)derived_type();
        assert(dt->nrefs == 1);
        assert(dt->super == (zsp_object_type_t *)base_type());
    }

    /* ExprNew inside a method: d.spawn() allocates child = new base(99) */
    assert(d->child == 0);
    derived__spawn(d);
    assert(d->child != 0);
    assert(d->child->base.refc == 1);
    assert(d->child->x == 99);
    assert(ZSP_VCALL(base_type_t, f, (base_t *)d->child) == 99);

    /* teardown: dropping d runs derived dtor (decref child) then base dtor */
    base_t *child = d->child;
    zsp_object_decref((zsp_object_t *)d);
    assert(child->base.refc == 0);    /* child reclaimed by refcount */
    zsp_object_free(&alloc, (zsp_object_t *)child);
    zsp_object_free(&alloc, (zsp_object_t *)d);

    zsp_object_decref((zsp_object_t *)b);
    zsp_object_free(&alloc, (zsp_object_t *)b);

    printf("class_model_slice: OK\n");
    return 0;
}
"""


@pytest.mark.skipif(_find_cc() is None, reason="no C compiler available")
def test_class_model_slice(tmp_path):
    cc = _find_cc()
    ctxt = _build_context()

    hp, cp = class_codegen.generate_class(ctxt, tmp_path, basename="model")
    (tmp_path / "harness.c").write_text(_HARNESS)

    exe = tmp_path / "slice"
    cmd = [
        cc, "-g", "-O0", "-Wall",
        f"-I{_INCLUDE}", f"-I{tmp_path}",
        str(cp), str(tmp_path / "harness.c"),
        str(_RT / "zsp_object.c"), str(_RT / "zsp_alloc.c"),
        "-o", str(exe),
    ]
    comp = subprocess.run(cmd, capture_output=True, text=True)
    assert comp.returncode == 0, (
        "compile failed:\n" + comp.stderr +
        "\n--- generated header ---\n" + Path(hp).read_text() +
        "\n--- generated source ---\n" + Path(cp).read_text()
    )

    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0, f"run failed:\n{run.stdout}\n{run.stderr}"
    assert "class_model_slice: OK" in run.stdout

#****************************************************************************
# Copyright 2019-2025 Matthew Ballance and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#****************************************************************************
"""
Class-model C code generation (non-synthesizable SW path).

Lowers core class-based SystemVerilog -- classes, single inheritance, virtual
methods, plain methods -- to C that runs on the zsp_object / zsp_class runtime
ABI. This is the Phase-3 vertical slice: a self-contained emitter that consumes
``ir.DataTypeClass`` definitions directly, independent of the component/RTL
pipeline.

ABI targeted (see share/include/zsp_class.h):
  - prefix-layout single inheritance: a derived struct embeds its base as the
    first member, so an up-cast is a zero-cost reinterpret;
  - the per-type descriptor doubles as the vtable (zsp_object_type_t base +
    one function pointer per virtual slot);
  - allocation funnels through zsp_object_alloc(); refcount via refc/dtor;
  - a precise GC root map (nrefs/ref_offsets) is emitted per class.

Field access is uniformly lowered as ``((<DeclClass>_t *)base)->name`` -- valid
for inherited fields because the declaring class is always a layout prefix.
Likewise a virtual call casts the receiver's type to the *slot-owning* class's
vtable (also a prefix), so dispatch is correct for every concrete type.
"""
from __future__ import annotations

import dataclasses as dc
from typing import Dict, List, Optional, Tuple

from zuspec.dataclasses import ir


# --------------------------------------------------------------------------
# Type mapping (minimal subset for the class slice)
# --------------------------------------------------------------------------
_INT_C = {
    (8, True): "int8_t", (8, False): "uint8_t",
    (16, True): "int16_t", (16, False): "uint16_t",
    (32, True): "int32_t", (32, False): "uint32_t",
    (64, True): "int64_t", (64, False): "uint64_t",
}


def _class_name(dt: ir.DataType) -> str:
    return dt.name or "anon"


def _is_class(dt: ir.DataType) -> bool:
    # A pure class -- exclude component/action specializations handled elsewhere.
    return isinstance(dt, ir.DataTypeClass) and not isinstance(
        dt, (ir.DataTypeComponent, ir.DataTypeAction))


def _is_handle_type(dt: Optional[ir.DataType]) -> bool:
    """True if a field of this type holds a managed object handle (GC root)."""
    return dt is not None and isinstance(dt, ir.DataTypeClass)


def map_type(dt: Optional[ir.DataType]) -> str:
    if dt is None:
        return "void"
    if isinstance(dt, ir.DataTypeInt):
        return _INT_C.get((dt.bits if dt.bits > 0 else 32, dt.signed), "int32_t")
    if _is_class(dt):
        return f"{_class_name(dt)}_t *"   # handles are pointers
    raise NotImplementedError(f"class_codegen: unsupported type {type(dt).__name__}")


# --------------------------------------------------------------------------
# Per-class analysis
# --------------------------------------------------------------------------
@dc.dataclass
class MethodInfo:
    func: ir.Function
    name: str
    is_virtual: bool
    is_ctor: bool
    slot_owner: Optional[str]     # class that first declares this virtual slot
    introduces_slot: bool         # True if this class adds a new vtable slot


@dc.dataclass
class ClassInfo:
    dt: ir.DataTypeClass
    name: str
    super_name: Optional[str]
    own_fields: List[ir.Field]
    methods: List[MethodInfo]
    # field name -> class that declares it (for prefix-cast access)
    field_decl: Dict[str, str]


def _is_virtual(func: ir.Function) -> bool:
    md = getattr(func, "metadata", None) or {}
    return bool(md.get("virtual"))


def _is_ctor(func: ir.Function) -> bool:
    return func.name in ("new", "__init__")


class ClassModel:
    """Resolves the class hierarchy into per-class layout/dispatch facts."""

    def __init__(self, ctxt: ir.Context):
        self.ctxt = ctxt
        self.classes: Dict[str, ClassInfo] = {}
        self._order: List[str] = []
        self._build()

    def _super_name(self, dt: ir.DataTypeClass) -> Optional[str]:
        s = getattr(dt, "super", None)
        if s is None:
            return None
        return _class_name(s)

    def _build(self):
        raw = {n: dt for n, dt in self.ctxt.type_m.items() if _is_class(dt)}

        # Emit bases before derived (topological by super chain).
        def visit(name: str, seen: set):
            if name in self.classes or name not in raw:
                return
            seen.add(name)
            dt = raw[name]
            sname = self._super_name(dt)
            if sname and sname in raw and sname not in seen:
                visit(sname, seen)
            self.classes[name] = self._analyze(dt, sname)
            self._order.append(name)

        for n in raw:
            visit(n, set())

    def _virtual_methods_upchain(self, super_name: Optional[str]) -> Dict[str, str]:
        """Map virtual-method-name -> slot-owner class, across all ancestors."""
        out: Dict[str, str] = {}
        chain: List[str] = []
        s = super_name
        while s and s in self.classes:
            chain.append(s)
            s = self.classes[s].super_name
        for cname in reversed(chain):   # base-most first
            for m in self.classes[cname].methods:
                if m.is_virtual and m.introduces_slot:
                    out[m.name] = cname
        return out

    def _field_decl_upchain(self, super_name: Optional[str]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        s = super_name
        chain: List[str] = []
        while s and s in self.classes:
            chain.append(s)
            s = self.classes[s].super_name
        for cname in reversed(chain):
            for f in self.classes[cname].own_fields:
                out[f.name] = cname
        return out

    def _analyze(self, dt: ir.DataTypeClass, super_name: Optional[str]) -> ClassInfo:
        own_fields = [f for f in (dt.fields or [])]
        inherited_virt = self._virtual_methods_upchain(super_name)

        methods: List[MethodInfo] = []
        for func in (dt.functions or []):
            virt = _is_virtual(func)
            ctor = _is_ctor(func)
            slot_owner = None
            introduces = False
            if virt:
                if func.name in inherited_virt:
                    slot_owner = inherited_virt[func.name]    # override
                else:
                    slot_owner = dt.name                      # new slot
                    introduces = True
            methods.append(MethodInfo(
                func=func, name=func.name, is_virtual=virt, is_ctor=ctor,
                slot_owner=slot_owner, introduces_slot=introduces))

        field_decl = self._field_decl_upchain(super_name)
        for f in own_fields:
            field_decl[f.name] = dt.name

        return ClassInfo(
            dt=dt, name=dt.name, super_name=super_name,
            own_fields=own_fields, methods=methods, field_decl=field_decl)

    def ordered(self) -> List[ClassInfo]:
        return [self.classes[n] for n in self._order]

    # vtable slots that exist on a class (own introduced + inherited), in order
    def vtable_slots(self, ci: ClassInfo) -> List[Tuple[str, str]]:
        """Return [(method_name, owner_class)] for all virtual slots, base-first."""
        slots: List[Tuple[str, str]] = []
        if ci.super_name and ci.super_name in self.classes:
            slots.extend(self.vtable_slots(self.classes[ci.super_name]))
        for m in ci.methods:
            if m.is_virtual and m.introduces_slot:
                slots.append((m.name, ci.name))
        return slots

    def concrete_impl(self, ci: ClassInfo, method_name: str) -> str:
        """Name of the C function implementing method_name for class ci.

        Walks up the hierarchy to find the most-derived override at/above ci.
        """
        cur: Optional[ClassInfo] = ci
        while cur is not None:
            for m in cur.methods:
                if m.name == method_name:
                    return f"{cur.name}__{method_name}"
            cur = self.classes.get(cur.super_name) if cur.super_name else None
        return f"{ci.name}__{method_name}"


# --------------------------------------------------------------------------
# Expression / statement lowering
# --------------------------------------------------------------------------
class _ExprLower:
    def __init__(self, model: ClassModel, ci: ClassInfo, func: ir.Function,
                 self_c: str = "self", var_map: Optional[Dict[str, str]] = None):
        self.m = model
        self.ci = ci
        self.func = func
        self.params = [a.arg for a in (func.args.args if func.args else [])]
        # Name resolution scope. In a plain method `self`/params are direct C
        # names; inside a coroutine they live in the frame `locals` struct, so
        # callers pass self_c="locals->self" and a var_map for params/locals.
        self.self_c = self_c
        self.var_map = var_map or {}

    def _var(self, name: str) -> str:
        return self.var_map.get(name, name)

    def field_access(self, base_c: str, field_name: str) -> str:
        decl = self.ci.field_decl.get(field_name, self.ci.name)
        if decl == self.ci.name:
            return f"{base_c}->{field_name}"
        # inherited: up-cast to the declaring class (a layout prefix)
        return f"(({decl}_t *)({base_c}))->{field_name}"

    def expr(self, e: ir.Expr) -> str:
        if isinstance(e, ir.ExprConstant):
            v = e.value
            if isinstance(v, bool):
                return "1" if v else "0"
            return str(v)
        if isinstance(e, ir.TypeExprRefSelf):
            return self.self_c
        if isinstance(e, ir.ExprRefParam):
            return self._var(e.name)
        if isinstance(e, ir.ExprRefLocal):
            return self._var(e.name)
        if isinstance(e, ir.ExprRefUnresolved):
            return e.name
        if isinstance(e, ir.ExprAttribute):
            base = e.value
            # super.method handled at call sites; bare attribute = field access
            base_c = self.expr(base)
            return self.field_access(base_c, e.attr)
        if isinstance(e, ir.ExprBin):
            return f"({self.expr(e.lhs)} {self._binop(e.op)} {self.expr(e.rhs)})"
        if isinstance(e, ir.ExprNew):
            return self._new(e)
        if isinstance(e, ir.ExprCall):
            return self._call(e)
        raise NotImplementedError(
            f"class_codegen: cannot lower expr {type(e).__name__}")

    def _is_super(self, e: ir.Expr) -> bool:
        return (isinstance(e, ir.ExprRefUnresolved) and e.name == "super")

    def _call(self, e: ir.ExprCall) -> str:
        func = e.func
        args_c = [self.expr(a) for a in e.args]
        if isinstance(func, ir.ExprAttribute):
            recv = func.value
            mname = func.attr
            # super.m(...) -> direct call to the super's impl
            if self._is_super(recv):
                super_ci = self.m.classes.get(self.ci.super_name)
                impl = self.m.concrete_impl(super_ci, mname) if super_ci else \
                    f"{self.ci.super_name}__{mname}"
                cast = f"({self.ci.super_name}_t *)({self.self_c})"
                return self._emit_call(impl, [cast] + args_c)
            # self.m(...) or obj.m(...)
            recv_c = self.expr(recv)
            mi = self._method_info(recv, mname)
            if mi is not None and mi.is_virtual:
                owner = mi.slot_owner
                all_args = ", ".join(args_c)
                tail = (", " + all_args) if all_args else ""
                return f"ZSP_VCALL({owner}_type_t, {mname}, {recv_c}{tail})"
            # non-virtual / static -> direct call
            impl = self._direct_impl(recv, mname)
            return self._emit_call(impl, [recv_c] + args_c)
        raise NotImplementedError("class_codegen: unsupported call target")

    def _emit_call(self, fn: str, args: List[str]) -> str:
        return f"{fn}({', '.join(args)})"

    def _recv_class(self, recv: ir.Expr) -> Optional[ClassInfo]:
        # self -> current class; otherwise rely on declared method lookup
        if isinstance(recv, ir.TypeExprRefSelf):
            return self.ci
        return None

    def _method_info(self, recv: ir.Expr, mname: str) -> Optional[MethodInfo]:
        ci = self._recv_class(recv)
        if ci is None:
            return None
        cur: Optional[ClassInfo] = ci
        while cur is not None:
            for m in cur.methods:
                if m.name == mname:
                    return m
            cur = self.m.classes.get(cur.super_name) if cur.super_name else None
        return None

    def _direct_impl(self, recv: ir.Expr, mname: str) -> str:
        ci = self._recv_class(recv)
        if ci is not None:
            return self.m.concrete_impl(ci, mname)
        return mname

    def _new(self, e: ir.ExprNew) -> str:
        cname = _class_name(e.datatype)
        args_c = [self.expr(a) for a in e.args]
        ctor = f"{cname}__new"
        # Allocation seam: a process/thread-wide default allocator. A real GC or
        # thread-local heap replaces this global without changing call sites.
        obj = f"ZSP_NEW({cname}_t, zsp_default_alloc, {cname}_type)"
        # Evaluate as a statement-expression: allocate then construct. The fresh
        # object carries refc==1, which the owning handle inherits (no incref).
        inner = ", ".join(["__o"] + args_c)
        return (f"({{ {cname}_t *__o = {obj}; {ctor}({inner}); __o; }})")

    def _binop(self, op) -> str:
        return {
            ir.BinOp.Add: "+", ir.BinOp.Sub: "-", ir.BinOp.Mult: "*",
            ir.BinOp.Div: "/", ir.BinOp.Mod: "%",
            ir.BinOp.BitAnd: "&", ir.BinOp.BitOr: "|", ir.BinOp.BitXor: "^",
            ir.BinOp.LShift: "<<", ir.BinOp.RShift: ">>",
            ir.BinOp.Eq: "==", ir.BinOp.NotEq: "!=",
            ir.BinOp.Lt: "<", ir.BinOp.LtE: "<=",
            ir.BinOp.Gt: ">", ir.BinOp.GtE: ">=",
            ir.BinOp.And: "&&", ir.BinOp.Or: "||",
        }[op]


class _StmtLower:
    def __init__(self, el: _ExprLower):
        self.el = el

    def block(self, stmts: List[ir.Stmt], indent: str) -> List[str]:
        out: List[str] = []
        for s in stmts or []:
            out.extend(self.stmt(s, indent))
        return out

    def stmt(self, s: ir.Stmt, indent: str) -> List[str]:
        if isinstance(s, ir.StmtReturn):
            if s.value is None:
                return [f"{indent}return;"]
            return [f"{indent}return {self.el.expr(s.value)};"]
        if isinstance(s, ir.StmtAssign):
            tgt = self.el.expr(s.targets[0])
            return [f"{indent}{tgt} = {self.el.expr(s.value)};"]
        if isinstance(s, ir.StmtExpr):
            return [f"{indent}{self.el.expr(s.expr)};"]
        if isinstance(s, ir.StmtIf):
            out = [f"{indent}if ({self.el.expr(s.test)}) {{"]
            out.extend(self.block(s.body, indent + "    "))
            if s.orelse:
                out.append(f"{indent}}} else {{")
                out.extend(self.block(s.orelse, indent + "    "))
            out.append(f"{indent}}}")
            return out
        raise NotImplementedError(
            f"class_codegen: cannot lower stmt {type(s).__name__}")


# --------------------------------------------------------------------------
# Coroutine (task / async method) lowering
# --------------------------------------------------------------------------
def _unwrap_await(e: ir.Expr) -> ir.Expr:
    return e.value if isinstance(e, ir.ExprAwait) else e


def _wait_time(stmt: ir.Stmt) -> Optional[ir.Expr]:
    """If *stmt* is a suspend point ``await self.wait(t)``, return ``t``."""
    if not isinstance(stmt, ir.StmtExpr):
        return None
    call = _unwrap_await(stmt.expr)
    if not (isinstance(call, ir.ExprCall)
            and isinstance(call.func, ir.ExprAttribute)
            and call.func.attr == "wait"
            and isinstance(call.func.value, ir.TypeExprRefSelf)
            and len(call.args) == 1):
        return None
    return call.args[0]


@dc.dataclass
class _Suspend:
    """How a coroutine block ends. ``None`` block.suspend = final block (return)."""
    kind: str                              # 'wait' | 'call'
    time: Optional[ir.Expr] = None         # wait: delay
    recv: Optional[ir.Expr] = None         # call: receiver expression
    method: Optional[str] = None           # call: method name
    args: List[ir.Expr] = dc.field(default_factory=list)  # call: arguments
    result: Optional[ir.Expr] = None       # call: lvalue for the return value


@dc.dataclass
class _CoBlock:
    stmts: List[ir.Stmt]
    suspend: Optional[_Suspend]            # suspend at end of block, or None
    ret_expr: Optional[ir.Expr] = None     # value for the final block's return


class _CoSplitter:
    """Splits a task body into blocks separated by suspend points.

    Suspend points are ``await self.wait(t)`` and blocking subtask calls
    (an ``await`` of an *async* method). Method async-ness is resolved against
    the receiver's class, so calls to plain functions stay inline.
    """

    def __init__(self, model: "ClassModel", ci: "ClassInfo"):
        self.m = model
        self.ci = ci

    def _recv_class(self, recv: ir.Expr) -> Optional["ClassInfo"]:
        if isinstance(recv, ir.TypeExprRefSelf):
            return self.ci
        return None

    def _resolve_async(self, recv: ir.Expr, mname: str) -> bool:
        ci = self._recv_class(recv)
        cur = ci
        while cur is not None:
            for fn_mi in cur.methods:
                if fn_mi.name == mname:
                    return fn_mi.func.is_async
            cur = self.m.classes.get(cur.super_name) if cur.super_name else None
        return False

    def _as_call_suspend(self, stmt: ir.Stmt) -> Optional[_Suspend]:
        """Detect a blocking subtask call, with or without a result assignment."""
        result = None
        expr = None
        if isinstance(stmt, ir.StmtExpr):
            expr = stmt.expr
        elif isinstance(stmt, ir.StmtAssign) and len(stmt.targets) == 1:
            expr = stmt.value
            result = stmt.targets[0]
        else:
            return None
        call = _unwrap_await(expr)
        if not (isinstance(call, ir.ExprCall)
                and isinstance(call.func, ir.ExprAttribute)):
            return None
        recv, mname = call.func.value, call.func.attr
        if mname == "wait":           # handled by _wait_time
            return None
        if not self._resolve_async(recv, mname):
            return None
        return _Suspend(kind="call", recv=recv, method=mname,
                        args=list(call.args), result=result)

    def split(self, body: List[ir.Stmt]) -> List[_CoBlock]:
        blocks: List[_CoBlock] = []
        cur: List[ir.Stmt] = []
        for s in body or []:
            t = _wait_time(s)
            if t is not None:
                blocks.append(_CoBlock(cur, _Suspend(kind="wait", time=t)))
                cur = []
                continue
            csusp = self._as_call_suspend(s)
            if csusp is not None:
                blocks.append(_CoBlock(cur, csusp))
                cur = []
                continue
            cur.append(s)
        blocks.append(_CoBlock(cur, None))
        return blocks


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------
class ClassEmitter:
    def __init__(self, model: ClassModel):
        self.m = model

    def _has_async(self) -> bool:
        return any(m.func.is_async
                   for ci in self.m.ordered() for m in ci.methods)

    # ---- struct + vtable declarations (header) ----
    def emit_header(self, basename: str) -> str:
        guard = f"INCLUDED_{basename.upper()}_H"
        L = [f"#ifndef {guard}", f"#define {guard}",
             '#include "zsp_object.h"', '#include "zsp_class.h"']
        if self._has_async():
            L.append('#include "zsp_timebase.h"')   # tasks -> coroutines
        L += ["",
              "/* Process-wide default allocator for `new`. A real GC/thread-local",
              "   heap replaces this without changing generated call sites. */",
              "extern zsp_alloc_t *zsp_default_alloc;", ""]
        for ci in self.m.ordered():
            L += self._struct_decl(ci) + [""]
            L += self._vtable_decl(ci) + [""]
            L += self._proto_decls(ci) + [""]
        L += [f"#endif /* {guard} */", ""]
        return "\n".join(L)

    def _struct_decl(self, ci: ClassInfo) -> List[str]:
        L = [f"typedef struct {ci.name}_s {{"]
        if ci.super_name:
            L.append(f"    {ci.super_name}_t up;")
        else:
            L.append("    zsp_object_t base;")
        for f in ci.own_fields:
            L.append(f"    {map_type(f.datatype)} {f.name};")
        L.append(f"}} {ci.name}_t;")
        return L

    def _vtable_decl(self, ci: ClassInfo) -> List[str]:
        L = [f"typedef struct {ci.name}_type_s {{"]
        if ci.super_name:
            L.append(f"    {ci.super_name}_type_t base;")
        else:
            L.append("    zsp_object_type_t base;")
        for m in ci.methods:
            if m.is_virtual and m.introduces_slot:
                L.append(f"    {self._fnptr(ci, m)};")
        L.append(f"}} {ci.name}_type_t;")
        return L

    def _fnptr(self, ci: ClassInfo, m: MethodInfo) -> str:
        ret = map_type(m.func.returns)
        params = ["void *self"] + self._param_decls(m.func)
        return f"{ret} (*{m.name})({', '.join(params)})"

    def _param_decls(self, func: ir.Function) -> List[str]:
        out = []
        args = func.args.args if func.args else []
        for a in args:
            ann = getattr(a, "annotation", None)
            # annotations from hand-built IR may carry a DataType in .ref
            dt = getattr(ann, "ref", None) if ann is not None else None
            cty = map_type(dt) if isinstance(dt, ir.DataType) else "int32_t"
            out.append(f"{cty} {a.arg}")
        return out

    def _proto_decls(self, ci: ClassInfo) -> List[str]:
        L = [f"{ci.name}_type_t *{ci.name}_type(void);"]
        for m in ci.methods:
            if m.func.is_async:
                # task -> coroutine entry (zsp_task_func signature)
                L.append(f"zsp_frame_t *{self._task_name(ci, m)}("
                         "zsp_timebase_t *, zsp_thread_t *, int, va_list *);")
                continue
            ret = map_type(m.func.returns)
            params = [f"{ci.name}_t *self"] + self._param_decls(m.func)
            L.append(f"{ret} {ci.name}__{m.name}({', '.join(params)});")
        return L

    def _task_name(self, ci: ClassInfo, m: MethodInfo) -> str:
        return f"{ci.name}__{m.name}_task"

    # ---- source ----
    def emit_source(self, header_name: str) -> str:
        L = [f'#include "{header_name}"', "#include <stddef.h>", ""]
        for ci in self.m.ordered():
            L += self._dtor(ci) + [""]
            L += self._type_singleton(ci) + [""]
            for m in ci.methods:
                L += self._method_body(ci, m) + [""]
        return "\n".join(L)

    def _dtor(self, ci: ClassInfo) -> List[str]:
        # Release managed-handle fields (refcount), then chain to super dtor.
        handles = [f for f in ci.own_fields if _is_handle_type(f.datatype)]
        L = [f"static void {ci.name}__dtor(zsp_object_t *o) {{"]
        if handles:
            L.append(f"    {ci.name}_t *self = ({ci.name}_t *)o;")
            for f in handles:
                L.append(f"    zsp_object_decref((zsp_object_t *)self->{f.name});")
        if ci.super_name:
            L.append(f"    {ci.super_name}__dtor(o);")
        if not handles and not ci.super_name:
            L.append("    (void)o;")
        L.append("}")
        return L

    def _refmap(self, ci: ClassInfo) -> Tuple[List[str], Optional[str]]:
        handles = [f for f in ci.own_fields if _is_handle_type(f.datatype)]
        if not handles:
            return [], None
        name = f"{ci.name}__refs"
        offs = ", ".join(f"offsetof({ci.name}_t, {f.name})" for f in handles)
        return [f"ZSP_REFMAP({ci.name}_t, {name}, {offs});"], name

    def _type_singleton(self, ci: ClassInfo) -> List[str]:
        refmap_lines, refmap_name = self._refmap(ci)
        L = list(refmap_lines)
        L += [
            f"{ci.name}_type_t *{ci.name}_type(void) {{",
            "    static int __init = 0;",
            f"    static {ci.name}_type_t __type;",
            "    if (!__init) {",
            "        zsp_object_type_init((zsp_object_type_t *)&__type);",
        ]
        base = "(zsp_object_type_t *)&__type"
        if ci.super_name:
            L.append(f"        __type.base = *{ci.super_name}_type();")
            L.append(f"        (({base}))->super = (zsp_object_type_t *){ci.super_name}_type();")
        else:
            L.append(f"        (({base}))->super = zsp_object__type();")
        L.append(f"        (({base}))->name = \"{ci.name}\";")
        L.append(f"        (({base}))->size = sizeof({ci.name}_t);")
        L.append(f"        (({base}))->dtor = &{ci.name}__dtor;")
        # install/override every virtual slot reachable on this class
        for mname, owner in self.m.vtable_slots(ci):
            impl = self.m.concrete_impl(ci, mname)
            slot = self._slot_lvalue(ci, mname, owner)
            L.append(f"        {slot} = (void *)&{impl};")
        if refmap_name:
            L.append(f"        ZSP_TYPE_SET_REFMAP(&__type, {refmap_name});")
        L += ["        __init = 1;", "    }", "    return &__type;", "}"]
        return L

    def _slot_lvalue(self, ci: ClassInfo, mname: str, owner: str) -> str:
        # Walk embedded `base` members from ci's vtable down to the owner.
        path = ["__type"]
        cur = ci.name
        while cur != owner:
            path.append("base")
            cur = self.m.classes[cur].super_name
        return ".".join(path) + f".{mname}"

    def _method_body(self, ci: ClassInfo, m: MethodInfo) -> List[str]:
        if m.func.is_async:
            return self._coroutine_body(ci, m)
        ret = map_type(m.func.returns)
        params = [f"{ci.name}_t *self"] + \
            [f"{c}" for c in self._param_decls(m.func)]
        el = _ExprLower(self.m, ci, m.func)
        sl = _StmtLower(el)
        L = [f"{ret} {ci.name}__{m.name}({', '.join(params)}) {{"]
        L += sl.block(m.func.body, "    ")
        L.append("}")
        return L

    def _coroutine_body(self, ci: ClassInfo, m: MethodInfo) -> List[str]:
        """Lower an async task to a switch/case coroutine on the timebase ABI.

        The body is split at suspend points (``await self.wait(t)``); each block
        becomes a ``case``. Persistent state (`self` + params) lives in the
        frame `locals` struct, so `self`/params resolve to `locals->...`.
        """
        if m.is_virtual:
            raise NotImplementedError(
                "class_codegen: virtual tasks not yet supported")

        task = self._task_name(ci, m)
        blocks = _CoSplitter(self.m, ci).split(m.func.body)
        param_args = [a for a in (m.func.args.args if m.func.args else [])]

        # A trailing `return <expr>` in the final block becomes a coroutine
        # return (zsp_timebase_return), not a C `return`.
        last = blocks[-1]
        if last.stmts and isinstance(last.stmts[-1], ir.StmtReturn):
            last.ret_expr = last.stmts.pop().value
        for blk in blocks:
            if any(isinstance(s, ir.StmtReturn) for s in blk.stmts):
                raise NotImplementedError(
                    "class_codegen: early return inside a task is not supported")

        # scope: self + params live in the frame locals
        var_map = {a.arg: f"locals->{a.arg}" for a in param_args}
        el = _ExprLower(self.m, ci, m.func,
                        self_c="locals->self", var_map=var_map)
        sl = _StmtLower(el)

        L = [f"zsp_frame_t *{task}(",
             "        zsp_timebase_t *tb,",
             "        zsp_thread_t *thread,",
             "        int idx,",
             "        va_list *args) {",
             "    zsp_frame_t *ret = thread->leaf;",
             "    (void)tb;",
             "    typedef struct {",
             f"        {ci.name}_t *self;"]
        for decl in self._param_decls(m.func):
            L.append(f"        {decl};")
        L += ["    } locals_t;", "",
              "    switch (idx) {"]

        n = len(blocks)
        for i, blk in enumerate(blocks):
            L.append(f"        case {i}: {{")
            if i == 0:
                L.append(f"            ret = zsp_timebase_alloc_frame("
                         f"thread, sizeof(locals_t), &{task});")
                L.append("            locals_t *locals = "
                         "zsp_frame_locals(ret, locals_t);")
                L.append("            if (args) {")
                L.append(f"                locals->self = "
                         f"({ci.name}_t *)va_arg(*args, void *);")
                for a in param_args:
                    L.append(f"                locals->{a.arg} = "
                             f"(int32_t)va_arg(*args, int);")
                L.append("            }")
            else:
                L.append("            locals_t *locals = "
                         "zsp_frame_locals(ret, locals_t);")
                L.append("            (void)locals;")
                # retrieve the result of the subtask call that suspended us
                prev = blocks[i - 1].suspend
                if prev is not None and prev.kind == "call" and prev.result:
                    tgt = el.expr(prev.result)
                    L.append(f"            {tgt} = (int32_t)thread->rval;")
            # straight-line statements of this block
            L += sl.block(blk.stmts, "            ")
            L += self._emit_suspend(ci, el, blk, i)
            L.append("        }")

        L += ["    }", "    return ret;", "}"]
        return L

    def _emit_suspend(self, ci: ClassInfo, el: _ExprLower,
                      blk: "_CoBlock", i: int) -> List[str]:
        s = blk.suspend
        ind = "            "
        if s is None:
            # final block: coroutine return (value or 0)
            val = el.expr(blk.ret_expr) if blk.ret_expr is not None else "0"
            return [f"{ind}ret = zsp_timebase_return(thread, (uintptr_t)({val}));",
                    f"{ind}break;"]
        if s.kind == "wait":
            return [f"{ind}ret->idx = {i + 1};",
                    f"{ind}zsp_timebase_wait(thread, {self._time_expr(el, s.time)});",
                    f"{ind}break;"]
        if s.kind == "call":
            # blocking subtask call: set resume, then trampoline into the subtask
            recv_c = el.expr(s.recv)
            recv_ci = self._recv_class(ci, s.recv)
            sub_task = self.m.concrete_impl(recv_ci, s.method) + "_task"
            call_args = ", ".join([f"&{sub_task}", recv_c] +
                                  [el.expr(a) for a in s.args])
            return [f"{ind}ret->idx = {i + 1};",
                    f"{ind}ret = zsp_timebase_call(thread, {call_args});",
                    f"{ind}break;"]
        raise AssertionError(f"unknown suspend kind {s.kind}")

    def _recv_class(self, ci: ClassInfo, recv: ir.Expr) -> ClassInfo:
        if isinstance(recv, ir.TypeExprRefSelf):
            return ci
        raise NotImplementedError(
            "class_codegen: subtask call on a non-self receiver not yet supported")

    def _time_expr(self, el: _ExprLower, e: ir.Expr) -> str:
        # Convention for the slice: a bare integer wait is nanoseconds.
        if isinstance(e, ir.ExprConstant):
            return f"ZSP_TIME_NS({e.value})"
        return f"ZSP_TIME_NS({el.expr(e)})"


def render(ctxt: ir.Context, basename: str = "model") -> Tuple[str, str]:
    """Render (header_text, source_text) for all classes in *ctxt*."""
    model = ClassModel(ctxt)
    em = ClassEmitter(model)
    header = em.emit_header(basename)
    source = em.emit_source(f"{basename}.h")
    return header, source


def generate_class(ctxt: ir.Context, output_dir, basename: str = "model"):
    """Write <basename>.h / <basename>.c for the classes in *ctxt*."""
    import os
    header, source = render(ctxt, basename)
    os.makedirs(output_dir, exist_ok=True)
    hp = os.path.join(output_dir, f"{basename}.h")
    cp = os.path.join(output_dir, f"{basename}.c")
    with open(hp, "w") as fp:
        fp.write(header)
    with open(cp, "w") as fp:
        fp.write(source)
    return hp, cp

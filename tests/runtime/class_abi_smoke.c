/*
 * Hand-written analogue of what the class-model codegen will emit for the
 * Phase-5 milestone slice. Validates the zsp_object / zsp_class ABI before the
 * generator targets it:
 *   - prefix-layout single inheritance (base_t embedded in derived_t)
 *   - per-type vtable (type descriptor + virtual slot), runtime dispatch
 *   - override + `super.f()` lowered as a direct (non-virtual) call
 *   - the zsp_object_alloc() allocation seam + refcount teardown via dtor
 *   - a managed-handle field with a precise GC root map (offsets emitted)
 *
 * Exit code 0 == all assertions held.
 */
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include "zsp_object.h"
#include "zsp_class.h"

/* ---- class base; int x; virtual function int f(); ---- */
typedef struct base_s {
    zsp_object_t base;
    int          x;
} base_t;

typedef struct base_type_s {
    zsp_object_type_t base;
    int (*f)(base_t *self);    /* virtual slot 0 */
} base_type_t;

static int   base__f(base_t *self) { return self->x; }   /* base impl   */
static void  base__dtor(zsp_object_t *o);
base_type_t *base__type(void);

/* ---- class derived extends base; base child; virtual function int f(); ---- */
typedef struct derived_s {
    base_t  up;            /* embedded base => zero-cost up-cast      */
    int     y;
    base_t *child;         /* managed handle (counts as a GC root)    */
} derived_t;

typedef struct derived_type_s {
    base_type_t base;      /* inherits base's vtable layout/slots     */
} derived_type_t;

/* derived overrides f(): super.f() + y, then exercises a direct super call */
static int derived__f(base_t *self_) {
    derived_t *self = (derived_t *)self_;
    return base__f(&self->up) + self->y;   /* `super.f()` == direct call */
}
static void  derived__dtor(zsp_object_t *o);
derived_type_t *derived__type(void);

/* ---- type descriptors (singletons), built like generated *_type_init ---- */
static void base__dtor(zsp_object_t *o) { (void)o; }

base_type_t *base__type(void) {
    static int __init = 0;
    static base_type_t __type;
    if (!__init) {
        zsp_object_type_init((zsp_object_type_t *)&__type);
        __type.base.super = zsp_object__type();
        __type.base.name  = "base";
        __type.base.size  = sizeof(base_t);
        __type.base.dtor  = &base__dtor;
        __type.f          = &base__f;     /* install virtual slot       */
        __init = 1;
    }
    return &__type;
}

/* precise GC root map: derived has one managed handle, `child` */
ZSP_REFMAP(derived_t, derived__refs, offsetof(derived_t, child));

static void derived__dtor(zsp_object_t *o) {
    derived_t *self = (derived_t *)o;
    zsp_object_decref((zsp_object_t *)self->child);  /* release handle  */
}

derived_type_t *derived__type(void) {
    static int __init = 0;
    static derived_type_t __type;
    if (!__init) {
        zsp_object_type_init((zsp_object_type_t *)&__type);
        __type.base.base.super = (zsp_object_type_t *)base__type();
        __type.base.base.name  = "derived";
        __type.base.base.size  = sizeof(derived_t);
        __type.base.base.dtor  = &derived__dtor;
        __type.base.f          = &derived__f;   /* override slot 0       */
        ZSP_TYPE_SET_REFMAP(&__type, derived__refs);
        __init = 1;
    }
    return &__type;
}

int main(void) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    /* obj = new() for both classes via the allocation seam */
    base_t    *b = ZSP_NEW(base_t, &alloc, base__type);
    derived_t *d = ZSP_NEW(derived_t, &alloc, derived__type);
    assert(b && d);
    assert(b->base.refc == 1 && d->up.base.refc == 1);

    b->x = 10;
    d->up.x = 3; d->y = 4;

    /* up-cast is zero-cost; assign a managed handle into derived.child */
    d->child = b;
    zsp_object_incref((zsp_object_t *)b);     /* handle assignment       */
    assert(b->base.refc == 2);

    /* virtual dispatch: base slot returns x; derived override returns x+y */
    assert(ZSP_VCALL(base_type_t, f, b) == 10);
    assert(ZSP_VCALL(base_type_t, f, (base_t *)d) == 7);   /* 3 + 4       */

    /* precise GC root map is reachable from the type descriptor */
    {
        zsp_object_type_t *dt = (zsp_object_type_t *)derived__type();
        assert(dt->nrefs == 1);
        assert(dt->ref_offsets[0] == offsetof(derived_t, child));
        assert(dt->super == (zsp_object_type_t *)base__type());  /* inherit */
    }

    /* refcount teardown: dropping d releases its handle on b */
    zsp_object_decref((zsp_object_t *)d);     /* d->dtor decrefs child b  */
    assert(b->base.refc == 1);
    zsp_object_free(&alloc, (zsp_object_t *)d);

    zsp_object_decref((zsp_object_t *)b);     /* b->refc -> 0, dtor runs  */
    assert(b->base.refc == 0);
    zsp_object_free(&alloc, (zsp_object_t *)b);

    printf("class_abi_smoke: OK\n");
    return 0;
}

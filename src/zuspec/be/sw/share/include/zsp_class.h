#ifndef INCLUDED_ZSP_CLASS_H
#define INCLUDED_ZSP_CLASS_H
/*
 * Class ABI for the SW (C coroutine) backend's non-synthesizable class model.
 *
 * This header packages the conventions that generated code targets when
 * lowering core class-based SystemVerilog (classes, single inheritance,
 * virtual methods) to C. It builds directly on zsp_object.h.
 *
 * Layout (single inheritance via prefix embedding)
 * ------------------------------------------------
 *   - Every instance begins with `zsp_object_t base;` (vptr=type + refc).
 *   - A derived class embeds its base struct as its first member, so an
 *     up-cast (Derived* -> Base*) is a zero-cost reinterpret. Field access is
 *     by offset, unchanged by derivation.
 *
 *       typedef struct base_s    { zsp_object_t base; int x; } base_t;
 *       typedef struct derived_s { base_t up;        int y; } derived_t;
 *
 * Vtable (type descriptor doubles as the vtable)
 * ----------------------------------------------
 *   - Each class T has a type struct whose first member is
 *     `zsp_object_type_t base;` followed by one function pointer per virtual
 *     method slot. Slots are inherited (same index in derived as in base) and
 *     overridden by storing the derived implementation in that slot.
 *   - `obj->base.type` points at the per-instance concrete type, so a virtual
 *     call dispatches through the most-derived override.
 *
 *       typedef struct base_type_s {
 *           zsp_object_type_t base;
 *           int (*f)(base_t *self);     // virtual slot 0
 *       } base_type_t;
 *
 * Dispatch
 * --------
 *   - Virtual call:  ZSP_VCALL(base_type_t, f, obj, ...)
 *   - Static call (non-virtual / `super.f()` / final): call the impl directly,
 *     e.g. base_t__f(ZSP_UPCAST(base_t, obj)). No vtable indirection; the C
 *     compiler can inline. The devirtualizer lowers a virtual call to this
 *     form whenever the concrete type is statically known.
 *
 * GC root map
 * -----------
 *   - For precise (future tracing) collection, each class emits its managed-
 *     handle field offsets via ZSP_REFMAP and wires them into the type
 *     descriptor with ZSP_TYPE_SET_REFMAP. Refcounting ignores the map; it
 *     exists so the collector can be swapped without changing generated code.
 */
#include <stddef.h>
#include <stdint.h>
#include "zsp_object.h"
#include "zsp_alloc.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Reinterpret `obj` as a pointer to class type `ctype` (up/down cast). */
#define ZSP_UPCAST(ctype, obj) ((ctype *)(obj))

/* Access the concrete type descriptor of `obj`, viewed as vtable `vtype`. */
#define ZSP_VTABLE(vtype, obj) \
    ((vtype *)(((zsp_object_t *)(obj))->type))

/*
 * Virtual call. `vtype` is the class's type/vtable struct, `method` the slot
 * name, `obj` the receiver (passed through as the first argument), followed by
 * any further arguments.
 *
 *   ZSP_VCALL(base_type_t, f, obj)          -> obj->type->f(obj)
 *   ZSP_VCALL(base_type_t, g, obj, a, b)    -> obj->type->g(obj, a, b)
 */
#define ZSP_VCALL(vtype, method, obj, ...) \
    (ZSP_VTABLE(vtype, obj)->method((void *)(obj), ##__VA_ARGS__))

/*
 * Declare a static, precise GC root map for class `ctype`: the byte offsets of
 * its managed-handle fields. Use offsetof() for each handle field.
 *
 *   ZSP_REFMAP(derived_t, derived__refs, offsetof(derived_t, child));
 */
#define ZSP_REFMAP(ctype, name, ...) \
    static const uint32_t name[] = { __VA_ARGS__ }

/* Wire a ZSP_REFMAP array into a type descriptor during *_type_init. */
#define ZSP_TYPE_SET_REFMAP(type_ptr, name) \
    do { \
        ((zsp_object_type_t *)(type_ptr))->nrefs = \
            (uint16_t)(sizeof(name) / sizeof((name)[0])); \
        ((zsp_object_type_t *)(type_ptr))->ref_offsets = (name); \
    } while (0)

/*
 * Allocate + construct an instance of class `ctype` whose type descriptor is
 * returned by `type_fn`. Storage comes from `alloc` with refc=1; the caller
 * then invokes the constructor. Evaluates to a `ctype *` (or NULL).
 */
#define ZSP_NEW(ctype, alloc, type_fn) \
    ((ctype *)zsp_object_alloc((alloc), (zsp_object_type_t *)(type_fn)()))

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_CLASS_H */

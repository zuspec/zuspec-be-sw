#ifndef INCLUDED_ZSP_OBJECT_H
#define INCLUDED_ZSP_OBJECT_H
#include <stdint.h>
#include <sys/types.h>
#include "zsp_types.h"
#include "zsp_alloc.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_object_s;
struct zsp_alloc_s;

typedef void (*zsp_init_f)(struct zsp_object_s *);
//typedef struct zsp_object_s *(*zsp_create_f)(
//    struct zsp_alloc_s *allocstruct zsp_object_s *);
typedef void (*zsp_dtor_f)(struct zsp_object_s *);

/*
 * Type descriptor shared by every object/class. A concrete class T embeds
 * this as the first member of its own type struct (T_type_t), appending its
 * virtual-method function pointers after it -- the descriptor doubles as the
 * vtable (see zsp_class.h, and zsp_struct_type_t for an existing example).
 *
 * GC-readiness: `nrefs`/`ref_offsets` form a *precise* root map -- the byte
 * offsets, within an instance, of fields that hold managed object handles
 * (zsp_object_t*). Reference counting ignores this map; a future tracing
 * collector uses it to follow live references without conservative scanning.
 * Codegen emits this map for every class from day one so the
 * arena -> refcount -> tracing progression is a runtime swap, not a codegen
 * change.
 */
typedef struct zsp_object_type_s {
    struct zsp_object_type_s    *super;
    const char                  *name;
    size_t                      size;
    zsp_dtor_f                  dtor;
    uint16_t                    nrefs;        /* # managed-handle fields */
    const uint32_t              *ref_offsets; /* byte offsets of those fields */
//    zsp_init_f                  create; // Likely to be type-specific
//    zsp_init_f                  init; // Likely to be type-specific
} zsp_object_type_t;

typedef struct zsp_object_s {
    zsp_object_type_t *type;
    int32_t            refc;
} zsp_object_t;

#define zsp_object_type(obj) \
    ((zsp_object_type_t *)(((zsp_object_t *)(obj))->type))

static inline void zsp_object_incref(zsp_object_t *obj) {
    if (obj) {
        obj->refc++;
    }
}

static inline void zsp_object_decref(zsp_object_t *obj) {
    if (obj && obj->refc) {
        obj->refc--;
        if (!obj->refc) {
            zsp_dtor_f dtor = zsp_object_type(obj)->dtor;
            if (dtor) {
                dtor(obj);
            }
        }
    }
}

zsp_object_type_t *zsp_object__type(void);

#define zsp_object(obj) ((zsp_object_t *)(obj))

zsp_object_type_t *zsp_object__type(void);

void zsp_object_type_init(zsp_object_type_t *t);

/*
 * Single allocation seam for managed objects. Allocates `type->size` bytes via
 * `alloc`, zeroes them, binds the type descriptor (vtable), and sets the
 * reference count to 1. All `new` lowering routes through here, so swapping the
 * collector (arena / refcount / tracing) behind `alloc` never touches codegen.
 * Returns NULL on allocation failure.
 */
zsp_object_t *zsp_object_alloc(zsp_alloc_t *alloc, zsp_object_type_t *type);

/*
 * Free an object's storage via `alloc`. Invoked by a collector (or directly by
 * refcount teardown after the dtor runs). Does not itself run the dtor.
 */
void zsp_object_free(zsp_alloc_t *alloc, zsp_object_t *obj);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_OBJECT_H */

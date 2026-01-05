#ifndef INCLUDED_ZSP_OBJECT_H
#define INCLUDED_ZSP_OBJECT_H
#include <sys/types.h>
#include "zsp_types.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_object_s;
struct zsp_alloc_s;

typedef void (*zsp_init_f)(struct zsp_object_s *);
//typedef struct zsp_object_s *(*zsp_create_f)(
//    struct zsp_alloc_s *allocstruct zsp_object_s *);
typedef void (*zsp_dtor_f)(struct zsp_object_s *);

typedef struct zsp_object_type_s {
    struct zsp_object_type_s    *super;
    const char                  *name;
    size_t                      size;
    zsp_dtor_f                  dtor;
//    zsp_init_f                  create; // Likely to be type-specific
//    zsp_init_f                  init; // Likely to be type-specific
} zsp_object_type_t;

typedef struct zsp_object_s {
    zsp_object_type_t *type;
    int32_t            refc;
} zsp_object_t;

#define zsp_object_type(obj) \
    ((zsp_object_type_t *)(((zsp_object_t *)(obj))->type))

static void zsp_object_incref(zsp_object_t *obj) {
    obj->refc++;
}

static void zsp_object_decref(zsp_object_t *obj) {
    if (obj && obj->refc) {
        obj->refc--;
        if (!obj->refc) {
            zsp_object_type(obj)->dtor(obj);
        }
    }
}

zsp_object_type_t *zsp_object__type(void);

#define zsp_object(obj) ((zsp_object_t *)(obj))

zsp_object_type_t *zsp_object__type(void);

void zsp_object_type_init(zsp_object_type_t *t);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_OBJECT_H */

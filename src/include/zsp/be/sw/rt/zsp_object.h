#ifndef INCLUDED_ZSP_OBJECT_H
#define INCLUDED_ZSP_OBJECT_H
#include <sys/types.h>
#include "zsp/be/sw/rt/zsp_types.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_object_s;
struct zsp_actor_s;

typedef void (*zsp_init_f)(struct zsp_actor_s *, struct zsp_object_s *);
typedef void (*zsp_dtor_f)(struct zsp_actor_s *, struct zsp_object_s *);

typedef struct zsp_object_type_s {
    struct zsp_object_type_s    *super;
    const char                  *name;
    size_t                      size;
    zsp_init_f                  init;
    zsp_dtor_f                  dtor;
} zsp_object_type_t;

typedef struct zsp_object_s {
    zsp_object_type_t *type;
    int32_t            refc;
} zsp_object_t;

zsp_object_type_t *zsp_object__type(void);

#define zsp_object_type(obj) \
    ((zsp_object_type_t *)(((zsp_object_t *)(obj))->type))

#define zsp_object(obj) ((zsp_object_t *)(obj))

zsp_object_type_t *zsp_object__type(void);

void zsp_object_type_init(zsp_object_type_t *t);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_OBJECT_H */

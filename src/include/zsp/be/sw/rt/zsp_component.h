#ifndef INCLUDED_ZSP_COMPONENT_H
#define INCLUDED_ZSP_COMPONENT_H
#include <stdint.h>
#include "zsp/be/sw/rt/zsp_alloc.h"
#include "zsp/be/sw/rt/zsp_object.h"

#ifdef _cplusplus
extern "C" {
#endif

struct zsp_component_s;

typedef struct zsp_component_type_s {
    zsp_object_type_t   __base;

    void (*init_down)(struct zsp_component_s *comp);
    void (*init_up)(struct zsp_component_s *comp);
} zsp_component_type_t;

typedef struct zsp_component_s {
    zsp_object_t            base;

    struct zsp_component_s  *parent;
    struct zsp_component_s  *sibling;
    struct zsp_component_s  *children;
    const char              *name;
} zsp_component_t;

void zsp_component_init(
    zsp_alloc_t         *alloc,
    zsp_component_t     *comp,
    const char          *name,
    zsp_component_t     *parent);

zsp_component_type_t *zsp_component__type();

#define zsp_component_type(comp) \
    ((zsp_component_type_t *)((comp)->base.type))

void zsp_component_do_init(zsp_component_t *comp);

#ifdef _cplusplus
}
#endif

#endif /* INCLUDED_ZSP_COMPONENT_H */

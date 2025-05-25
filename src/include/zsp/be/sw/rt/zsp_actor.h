#ifndef INCLUDED_ZSP_ACTOR_H
#define INCLUDED_ZSP_ACTOR_H
#include "zsp/be/sw/rt/zsp_actor_base.h"
#include "zsp/be/sw/rt/zsp_component.h"

typedef struct zsp_actor_s {
    zsp_actor_base_t    base;
    zsp_component_t     comp;
} zsp_actor_t;

#define zsp_actor(comp_t) struct { \
    zsp_actor_base_t    base; \
    comp_t ## _t        comp; \
    }


#endif /* INCLUDED_ZSP_ACTOR_H */

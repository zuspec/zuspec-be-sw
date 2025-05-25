
#include "zsp/be/sw/rt/zsp_actor.h"
#include "zsp/be/sw/rt/zsp_component.h"
#include <string.h>
#include <stdlib.h>

static void zsp_component_dtor(zsp_component_t *comp) {
    if (comp->sibling) {
        zsp_component_dtor(comp->sibling);
    }
    if (comp->parent && comp->parent->children == comp) {
        comp->parent->children = comp->sibling;
    }
    free((void*)comp->name);
    free(comp);
}

zsp_component_type_t *zsp_component__type() {
    static int __init = 0;
    static zsp_component_type_t __type;
    if (__init == 0) {
        ((zsp_object_type_t *)&__type)->super = 0;
        ((zsp_object_type_t *)&__type)->name = "zsp_component";
        ((zsp_object_type_t *)&__type)->dtor = (zsp_dtor_f)&zsp_component_dtor;
        __type.do_init = 0;
        __init = 1;
    }
    return &__type;
}

void zsp_component_init(
    zsp_actor_t         *actor,
    zsp_component_t     *comp,
    const char          *name,
    zsp_component_t     *parent) {
    comp->parent = parent;
    comp->sibling = 0;
    comp->children = 0;
    ((zsp_object_t *)comp)->type = (zsp_object_type_t *)zsp_component__type();

    if (parent) {
        // Connect ourselves in as a child
        comp->sibling = parent->children;
        parent->children = comp;
    }

//    comp->name = strdup(name);
}

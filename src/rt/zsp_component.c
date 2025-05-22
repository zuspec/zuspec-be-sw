
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

static void zsp_component_init_down(zsp_component_t *comp) {
}

static void zsp_component_init_up(zsp_component_t *comp) {
}

static zsp_component_type_t __zsp_component_type = {
    .__base = {
        .super = 0,
        .name = "zsp_component",
        .dtor = (void (*)(zsp_object_t *))&zsp_component_dtor,
    },
    .init_down = &zsp_component_init_down,
    .init_up = &zsp_component_init_up
};

void zsp_component_init(
    zsp_alloc_t         *alloc,
    zsp_component_t     *comp,
    const char          *name,
    zsp_component_t     *parent) {
    comp->parent = parent;
    comp->sibling = 0;
    comp->children = 0;
    comp->base.type = (zsp_object_type_t *)&__zsp_component_type;

    if (parent) {
        // Connect ourselves in as a child
        comp->sibling = parent->children;
        parent->children = comp;
    }

    comp->name = strdup(name);
}

void zsp_component_do_init(zsp_component_t *comp) {
    zsp_component_type(comp)->init_down(comp);

    if (comp->sibling) {
        zsp_component_do_init(comp->sibling);
    }

    if (comp->children) {
        zsp_component_do_init(comp->children);
    }

    zsp_component_type(comp)->init_up(comp);
}

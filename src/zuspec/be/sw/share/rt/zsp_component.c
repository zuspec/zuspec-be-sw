
#include <string.h>
#include <stdlib.h>
#include "zsp_alloc.h"
#include "zsp_component.h"
#include "zsp_init_ctxt.h"
#include "zsp_list.h"

static void zsp_component_dtor(zsp_component_t *comp) {
    if (comp->sibling) {
        zsp_component_dtor(comp->sibling);
    }
    if (comp->parent && comp->parent->children == comp) {
        comp->parent->children = comp->sibling;
    }
//    free((void*)comp->name);
//    free(comp);
}

static void zsp_component__do_init(zsp_component_t *self) {

    // Call init_down execs
    zsp_component_type(self)->init_down(self);

    if (self->children) {
        zsp_component_t *c = self->children;
        
        // Propagate component types up
        while (c) {
            zsp_int_obj_map_iterator_t it;

            zsp_component_type(c)->do_init(self);

            // On the 'up' path, aggregate comp_type map
            for (it=zsp_int_obj_map_iter(&c->comp_t_m); 
                zsp_int_obj_map_iter_valid(&it); zsp_int_obj_map_iter_next(&it)) {
                int32_t i;
                zsp_ptr_list_t *insts = 0;
                zsp_ptr_list_t *c_insts = zsp_int_obj_map_iter_second(&it);
                zsp_component_type_t *comp_t = (zsp_component_type_t *)zsp_int_obj_map_iter_first(&it);
                if (zsp_int_obj_map_exists(&self->comp_t_m, (intptr_t)comp_t)) {
                    insts = zsp_int_obj_map_get(&self->comp_t_m, comp_t);
                } else {
                    zsp_alloc_t *alloc = 0;
                    insts = zsp_ptr_list_new(alloc);
                    zsp_int_obj_map_insert(&self->comp_t_m, (intptr_t)comp_t, insts);
                }

                for (i=0; i<zsp_list(&c_insts)->sz; i++) {
                    zsp_ptr_list_push_back(insts, zsp_ptr_list_at(&c_insts, i));
                }
            }

            c = c->sibling;
        }
        {
            // Add ourselves to our map
            zsp_int_obj_map_iterator_t it;
            zsp_ptr_list_t *insts = 0;
            zsp_component_type_t *comp_t = zsp_component_type(self);

            if (zsp_int_obj_map_exists(&self->comp_t_m, comp_t)) {
                insts = (zsp_ptr_list_t *)zsp_int_obj_map_get(&self->comp_t_m, comp_t);
            } else {
                zsp_alloc_t *alloc = 0;
                insts = zsp_ptr_list_new(alloc);
                zsp_int_obj_map_insert(&self->comp_t_m, (intptr_t)comp_t, insts);
            }
            zsp_ptr_list_push_back(insts, comp_t);
        }


    }

    zsp_component_type(self)->init_up(self);
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
    struct zsp_init_ctxt_s  *ctxt,
    zsp_component_t         *comp,
    const char              *name,
    zsp_component_t         *parent) {
    comp->parent = parent;
    comp->sibling = 0;
    comp->children = 0;

    // TODO: initialize map

    ((zsp_object_t *)comp)->type = (zsp_object_type_t *)zsp_component__type();

    zsp_int_obj_map_init(&comp->comp_t_m, ctxt->alloc);

    if (parent) {
        // Connect ourselves in as a child
        comp->sibling = parent->children;
        parent->children = comp;
    }

//    comp->name = strdup(name);
}

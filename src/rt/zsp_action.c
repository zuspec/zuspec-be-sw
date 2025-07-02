#include "zsp/be/sw/rt/zsp_action.h"
#include "zsp/be/sw/rt/zsp_alloc.h"
#include "zsp/be/sw/rt/zsp_thread.h"

void zsp_action_type_init(zsp_action_type_t *t) {
    zsp_struct_type_init((zsp_struct_type_t *)t);
    ((zsp_object_type_t *)t)->super = zsp_struct__type();
    ((zsp_object_type_t *)t)->name = "zsp_action";
    t->comp_t = 0; // Set to the appropriate component type if needed
    t->body = 0; // Initialize body to NULL
}

zsp_action_type_t *zsp_action__type(void) {
    static int __init = 0;
    static zsp_action_type_t __type;
    if (__init == 0) {
        zsp_struct_type_init((zsp_struct_type_t *)&__type);
        __init = 1;
    }

    return &__type;
}

void zsp_action_init(
    zsp_alloc_t     *alloc, 
    zsp_action_t    *this_p) {
    zsp_struct_init(alloc, zsp_struct(this_p));
//    this_p->body = 0;
}

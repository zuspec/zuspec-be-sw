#include <string.h>
#include "zsp_list.h"

static void zsp_obj_list_dtor(zsp_obj_list_t *list) {
    int32_t i;
    // Release all elements
    for (i=0; i<list->base.sz; i++) {
        zsp_object_decref(list->store[i]);
    }
    
    // Release the store
    list->base.alloc->free(list->base.alloc, list->store);
}

static void zsp_obj_list_reset(zsp_obj_list_t *list) {
    int32_t i;
    // Release all elements
    for (i=0; i<list->base.sz; i++) {
        zsp_object_decref(list->store[i]);
    }
    list->base.sz = 0;
}

zsp_list_type_t *zsp_obj_list__type() {
    static int initialized = 0;
    static zsp_list_type_t type;
    if (!initialized) {
        type.base.super = zsp_object__type();
        type.base.name = "zsp_obj_list";
        type.base.dtor = (zsp_dtor_f)&zsp_obj_list_dtor;
        type.reset = (zsp_list_reset_f)&zsp_obj_list_reset;
        initialized = 1;
    }
    return &type;
}

zsp_ptr_list_t *zsp_ptr_list_new(struct zsp_alloc_s *alloc) {
    zsp_ptr_list_t *l = (zsp_ptr_list_t *)alloc->alloc(alloc, sizeof(zsp_ptr_list_t));
    // TODO: connect proper type
    return l;
}

void zsp_ptr_list_push_back(zsp_ptr_list_t *l, void *obj) {
    if (zsp_list(l)->sz >= zsp_list(l)->ext) {
        // Resize
        int32_t new_sz = (zsp_list(l)->sz)?(2*zsp_list(l)->sz):4;
        void **store = (void **)zsp_list(l)->alloc->alloc(zsp_list(l)->alloc, new_sz*sizeof(void *));
        if (zsp_list(l)->sz) {
            memcpy(store, l->store, zsp_list(l)->sz*sizeof(void *));
            zsp_list(l)->alloc->free(zsp_list(l)->alloc, l->store);
        }
        l->store = store;
    }
    l->store[zsp_list(l)->sz++] = obj;
}

void zsp_obj_list_init(
    zsp_obj_list_t  *list,
    zsp_alloc_t     *alloc) {
    zsp_object(list)->type = zsp_obj_list__type();
    list->base.alloc = alloc;
    list->base.sz  = 0;
    list->base.ext = 0;
    list->store = 0;
}

// void zsp_list_dtor(zsp_list_t *list) {
//     if (list->data && list->alloc->free) {
//         list->alloc->free(list->alloc, (void *)list->data);
//     }
// }


#include <string.h>
#include "zsp_object.h"

static void zsp_object__dtor(struct zsp_object_s *this_p) {

}

void zsp_object_type_init(zsp_object_type_t *t) {
    ((zsp_object_type_t *)t)->super = 0;
    ((zsp_object_type_t *)t)->name = "zsp_object";
    ((zsp_object_type_t *)t)->size = sizeof(zsp_object_t);
    ((zsp_object_type_t *)t)->dtor = (zsp_dtor_f)&zsp_object__dtor;
    ((zsp_object_type_t *)t)->nrefs = 0;
    ((zsp_object_type_t *)t)->ref_offsets = 0;
}

zsp_object_t *zsp_object_alloc(zsp_alloc_t *alloc, zsp_object_type_t *type) {
    size_t sz = (type->size > sizeof(zsp_object_t)) ? type->size : sizeof(zsp_object_t);
    zsp_object_t *obj = (zsp_object_t *)alloc->alloc(alloc, sz);
    if (obj) {
        memset(obj, 0, sz);
        obj->type = type;
        obj->refc = 1;
    }
    return obj;
}

void zsp_object_free(zsp_alloc_t *alloc, zsp_object_t *obj) {
    if (obj) {
        alloc->free(alloc, obj);
    }
}

zsp_object_type_t *zsp_object__type(void) {
    static int __init = 0;
    static zsp_object_type_t __type;
    if (__init == 0) {
        zsp_object_type_init(&__type);
        __init = 1;
    }

    return &__type;
}

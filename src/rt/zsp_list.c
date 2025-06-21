#include "zsp/be/sw/rt/zsp_list.h"

void zsp_list_init(
    zsp_list_t      *list,
    zsp_alloc_t     *alloc,
    uint32_t        it_sz,
    uint32_t        size) {
    
    list->alloc = alloc;
    list->elem_sz = it_sz;
    list->size = size;
    list->idx = 0;
    if (size > 0) {
        list->data = (uintptr_t)alloc->alloc(alloc, size*it_sz);
    } else {
        list->data = 0;
    }
}

void zsp_list_reset(zsp_list_t *list) {
    list->idx = 0;
}

void zsp_list_dtor(zsp_list_t *list) {
    if (list->data && list->alloc->free) {
        list->alloc->free(list->alloc, (void *)list->data);
    }
}

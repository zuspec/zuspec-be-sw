
#ifndef INCLUDED_ZSP_LIST_H
#define INCLUDED_ZSP_LIST_H
#include <stdint.h>
#include "zsp/be/sw/rt/zsp_alloc.h"

typedef struct zsp_list_s {
    zsp_alloc_t     *alloc; // Memory allocator
    uint32_t        idx;
    uint32_t        elem_sz;
    uint32_t        size;
    uintptr_t       data;
} zsp_list_t;


void zsp_list_init(
    zsp_list_t *list, 
    zsp_alloc_t *alloc, 
    uint32_t    it_sz,
    uint32_t size);

void zsp_list_reset(zsp_list_t *list);

void zsp_list_dtor(zsp_list_t *list);


#endif /* INCLUDED_ZSP_LIST_H */
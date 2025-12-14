
#ifndef INCLUDED_ZSP_LIST_H
#define INCLUDED_ZSP_LIST_H
#include <stdint.h>
#include "zsp_alloc.h"
#include "zsp_object.h"

struct zsp_list_s;

typedef void (*zsp_list_reset_f)(struct zsp_list_s *);

typedef struct zsp_list_type_s {
    zsp_object_type_t       base;
    zsp_list_reset_f        reset;
} zsp_list_type_t;

typedef struct zsp_list_s {
    zsp_object_t        base;
    zsp_alloc_t         *alloc;
    uint32_t            sz;
    uint32_t            ext;
} zsp_list_t;

#define zsp_list(obj) ((zsp_list_t *)(obj))

typedef struct zsp_obj_list_s {
    zsp_list_t          base;
    zsp_object_t        **store;
} zsp_obj_list_t;

typedef struct zsp_ptr_list_s {
    zsp_list_t          base;
    void                **store;
} zsp_ptr_list_t;

static void *zsp_ptr_list_at(zsp_ptr_list_t *l, int32_t idx) {
    return l->store[idx];
}

zsp_ptr_list_t *zsp_ptr_list_new(struct zsp_alloc_s *alloc);

void zsp_ptr_list_push_back(zsp_ptr_list_t *l, void *obj);

#define zsp_list_type(list) (zsp_list_type_t *)zsp_object_type(list)

void zsp_list_init(
    zsp_list_t *list, 
    zsp_alloc_t *alloc, 
    uint32_t    it_sz,
    uint32_t size);

void zsp_obj_list_init(
    zsp_obj_list_t  *list,
    zsp_alloc_t     *alloc);

void zsp_list_reset(zsp_list_t *list);

void zsp_list_dtor(zsp_list_t *list);


#endif /* INCLUDED_ZSP_LIST_H */
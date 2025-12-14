
#ifndef INCLUDED_ZSP_MAP_H
#define INCLUDED_ZSP_MAP_H
#include "zsp_alloc.h"
#include "zsp_object.h"
#include <stdint.h>

struct zsp_int_obj_map_type_s;

typedef struct zsp_int_obj_map_store_s {
    intptr_t            key;
    zsp_object_t        *val;
} zsp_int_obj_map_store_t;

typedef struct zsp_map_s {
    zsp_object_t                base;
    zsp_alloc_t                 *alloc;
    uint32_t                    flags;
    int32_t                     sz;
    int32_t                     ext;
} zsp_map_t;

typedef struct zsp_int_obj_map_s {
    zsp_map_t                   base;
    zsp_int_obj_map_store_t     *store;
} zsp_int_obj_map_t;

typedef struct zsp_int_obj_map_iterator_s {
    zsp_int_obj_map_t           *map;
    int32_t                     idx;
} zsp_int_obj_map_iterator_t;

typedef struct zsp_int_int_map_s {
    zsp_map_t                   base;
} zsp_int_int_map_t;

#define zsp_map(obj) ((zsp_map_t *)(obj))

typedef struct zsp_int_obj_map_type_s {
    zsp_object_type_t           base;

} zsp_int_obj_map_type_t;

void zsp_int_obj_map_init(
    zsp_int_obj_map_t   *map,
    zsp_alloc_t         *alloc);

void zsp_int_obj_map_insert(
    zsp_int_obj_map_t   *map,
    intptr_t            key,
    zsp_object_t        *val);

int32_t zsp_int_obj_map_exists(
    zsp_int_obj_map_t   *map,
    intptr_t            key);

zsp_object_t *zsp_int_obj_map_get(
    zsp_int_obj_map_t   *map,
    intptr_t            key);

zsp_int_obj_map_iterator_t zsp_int_obj_map_iter(zsp_int_obj_map_t *map);

int32_t zsp_int_obj_map_iter_valid(zsp_int_obj_map_iterator_t *it);

void zsp_int_obj_map_iter_next(zsp_int_obj_map_iterator_t *it);

intptr_t zsp_int_obj_map_iter_first(zsp_int_obj_map_iterator_t *it);

zsp_object_t *zsp_int_obj_map_iter_second(zsp_int_obj_map_iterator_t *it);


#endif /* INCLUDED_ZSP_MAP_H */
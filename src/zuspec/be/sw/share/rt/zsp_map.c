
#include <string.h>
#include "zsp_map.h"

static void zsp_int_obj_map_dtor(zsp_int_obj_map_t *map) {

}

zsp_int_obj_map_type_t *zsp_int_obj_map__type() {
    static zsp_int_obj_map_type_t type;
    static int initialized = 0;

    if (!initialized) {
        initialized = 1;
    }

    return &type;
}

void zsp_int_obj_map_init(
    zsp_int_obj_map_t   *map,
    zsp_alloc_t         *alloc) {
    zsp_object(map)->type = (zsp_object_type_t *)zsp_int_obj_map__type();
    zsp_map(map)->alloc = alloc;
    zsp_map(map)->flags = 0;
    zsp_map(map)->sz = 0;
    zsp_map(map)->ext = 0;
    map->store = 0;
}

void zsp_int_obj_map_insert(
    zsp_int_obj_map_t   *map,
    intptr_t            key,
    zsp_object_t        *val) {
    int32_t i;
    // First, see if the key exists
    for (i=0; i<zsp_map(map)->sz; i++) {
        if (map->store[i].key == key) {
            // Replace the element here
            zsp_object_decref(map->store[i].val);
            map->store[i].val = val;
        }
    }
    if (i == zsp_map(map)->sz) {
        // Need to insert
        if (zsp_map(map)->sz >= zsp_map(map)->ext) {
            // Need to resize
            int32_t new_sz = (zsp_map(map)->sz)?(2*zsp_map(map)->sz):4;
            zsp_int_obj_map_store_t *store = 
                (zsp_int_obj_map_store_t *)zsp_map(map)->alloc->alloc(
                    zsp_map(map)->alloc, 
                    (new_sz * sizeof(zsp_int_obj_map_store_t)));
            if (map->store) {
                memcpy(store, map->store,
                    zsp_map(map)->sz * sizeof(zsp_int_obj_map_store_t));
                zsp_map(map)->alloc->free(zsp_map(map)->alloc, map->store);
            }
            map->store = store;
        }
        map->store[zsp_map(map)->sz].key = key;
        map->store[zsp_map(map)->sz].val = val;
    }
    zsp_object_incref(val);
}

int32_t zsp_int_obj_map_exists(
    zsp_int_obj_map_t   *map,
    intptr_t            key) {
    int32_t i, ret = 0;
    for (i=0; i<zsp_map(map)->sz; i++) {
        if (map->store[i].key == key) {
            ret = 1;
            break;
        }
    }
    return ret;
}

zsp_object_t *zsp_int_obj_map_get(
    zsp_int_obj_map_t   *map,
    intptr_t            key) {
    zsp_object_t *ret = 0;
    int32_t i;
    for (i=0; i<zsp_map(map)->sz; i++) {
        if (map->store[i].key == key) {
            ret = map->store[i].val;
            break;
        }
    }
    return ret;
}

zsp_int_obj_map_iterator_t zsp_int_obj_map_iter(zsp_int_obj_map_t *map) {
    zsp_int_obj_map_iterator_t it = {.map=map, .idx=0};

    return it;
}

int32_t zsp_int_obj_map_iter_valid(zsp_int_obj_map_iterator_t *it) {
    return (it->idx < zsp_map(it->map)->sz);
}

void zsp_int_obj_map_iter_next(zsp_int_obj_map_iterator_t *it) {
    it->idx++;
}

intptr_t zsp_int_obj_map_iter_first(zsp_int_obj_map_iterator_t *it) {
    return it->map->store[it->idx].key;
}

zsp_object_t *zsp_int_obj_map_iter_second(zsp_int_obj_map_iterator_t *it) {
    return it->map->store[it->idx].val;
}
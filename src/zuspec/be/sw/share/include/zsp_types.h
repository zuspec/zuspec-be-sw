
#ifndef INCLUDED_ZSP_TYPES_H
#define INCLUDED_ZSP_TYPES_H
#include <stdint.h>
#include <stdbool.h>

typedef bool zsp_bool_t;

/* Stub type for unresolved resource-claim pointers (e.g. async-with lock() as claim). */
typedef struct _zsp_stub_s {
    struct _zsp_stub_s *t;
    uint32_t (*execute)(uint32_t, uint32_t, uint32_t);
    uint32_t (*access)(uint32_t, uint32_t, uint32_t);
} _zsp_stub_t;

#endif /* INCLUDED_ZSP_TYPES_H */

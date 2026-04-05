
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

/* Multi-return struct types used for tuple-unpack lowering (a, b = f(...)). */
typedef struct { uint32_t v0; uint32_t v1; } _zsp_tuple2_t;
typedef struct { uint32_t v0; uint32_t v1; uint32_t v2; } _zsp_tuple3_t;
typedef struct { uint32_t v0; uint32_t v1; uint32_t v2; uint32_t v3; } _zsp_tuple4_t;

#endif /* INCLUDED_ZSP_TYPES_H */

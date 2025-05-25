
#ifndef INCLUDED_ZSP_TYPES_H
#define INCLUDED_ZSP_TYPES_H
#include <stdint.h>

#ifdef __cplusplus
    typedef bool zsp_bool_t;
#else
typedef enum {
    false = 0,
    true = 1
} zsp_bool_t;
#endif


#endif /* INCLUDED_ZSP_TYPES_H */

#ifndef INCLUDED_ZSP_MODEL_H
#define INCLUDED_ZSP_MODEL_H
#include "zsp_api.h"

struct zsp_component_type_s;

typedef struct zsp_model_s {
    struct zsp_component_type_s **comp_types;
    const char **methods;
} zsp_model_t;

/**
 * Returns a null-terminated array of method name/type pairs
 */
//const char **zsp_get_method_types();


#endif /* INCLUDED_ZSP_MODEL_H */

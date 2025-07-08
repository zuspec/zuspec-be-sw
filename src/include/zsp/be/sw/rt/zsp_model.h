#ifndef INCLUDED_ZSP_MODEL_H
#define INCLUDED_ZSP_MODEL_H
#include "zsp/be/sw/rt/zsp_actor_base.h"
#include "zsp/be/sw/rt/zsp_api.h"

struct zsp_action_type_s;
struct zsp_component_type_s;

typedef struct zsp_model_s {
    struct zsp_action_type_s **action_types;
    struct zsp_component_type_s **comp_types;
    const char **methods;
} zsp_model_t;

/**
 * Returns a null-terminated array of actor types. 
 */
//zsp_actor_type_t **zsp_get_actor_types();

/**
 * Returns a null-terminated array of method name/type pairs
 */
//const char **zsp_get_method_types();


#endif /* INCLUDED_ZSP_MODEL_H */

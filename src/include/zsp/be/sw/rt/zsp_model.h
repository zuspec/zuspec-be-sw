#ifndef INCLUDED_ZSP_MODEL_H
#define INCLUDED_ZSP_MODEL_H
#include "zsp/be/sw/rt/zsp_actor_base.h"
#include "zsp/be/sw/rt/zsp_api.h"

/**
 * Returns a null-terminated array of actor types. 
 */
zsp_actor_type_t **zsp_get_actor_types();

/**
 * Returns a null-terminated array of method name/type pairs
 */
const char **zsp_get_method_types();


#endif /* INCLUDED_ZSP_MODEL_H */

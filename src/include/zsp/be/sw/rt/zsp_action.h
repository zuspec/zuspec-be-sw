
#ifndef INCLUDED_ZSP_ACTION_H
#define INCLUDED_ZSP_ACTION_H
#include "zsp/be/sw/rt/zsp_struct.h"
#include "zsp/be/sw/rt/zsp_thread.h"

typedef struct zsp_action_type_s {
    zsp_struct_type_t      base;

} zsp_action_type_t;

typedef struct zsp_action_s {
    zsp_struct_t           base;
    zsp_task_func          body;

} zsp_action_t;

#endif /* INCLUDED_ZSP_ACTION_H */

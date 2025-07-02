#ifndef INCLUDED_ZSP_ACTOR_H
#define INCLUDED_ZSP_ACTOR_H
#include "zsp/be/sw/rt/zsp_api.h"
#include "zsp/be/sw/rt/zsp_action.h"
#include "zsp/be/sw/rt/zsp_actor_base.h"
#include "zsp/be/sw/rt/zsp_component.h"
#include "zsp/be/sw/rt/zsp_executor.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_frame_s;
struct zsp_thread_s;

typedef struct zsp_actor_s {
    zsp_actor_base_t    base;
    zsp_component_t     comp;
} zsp_actor_t;


#define zsp_actor(comp_t, executor_t) struct { \
    zsp_actor_base_t    base; \
    comp_t ## _t        comp; \
    }

void zsp_actor_init(
    zsp_actor_t             *actor,
    zsp_api_t               *api,
    zsp_component_type_t    *comp_t,
    zsp_action_type_t       *action_t);

void zsp_actor_elab(zsp_actor_t *actor);

// Starts a new thread for the actor
struct zsp_thread_s *zsp_actor_start(
    zsp_actor_t             *actor,
    zsp_scheduler_t         *sched,
    void                    *action_args);

#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_ACTOR_H */

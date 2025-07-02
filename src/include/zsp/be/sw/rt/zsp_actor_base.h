
#ifndef INCLUDED_ZSP_ACTOR_BASE_H
#define INCLUDED_ZSP_ACTOR_BASE_H
#include "zsp/be/sw/rt/zsp_object.h"
#include "zsp/be/sw/rt/zsp_thread.h"

struct zsp_api_s;
struct zsp_actor_base_s;

typedef struct zsp_actor_type_s {
    const char          *name;
    size_t              size;
    void (*init)(
        struct zsp_actor_base_s *actor, 
        struct zsp_api_s        *api);
    zsp_thread_t *(*run)(
        struct zsp_actor_base_s *actor,
        struct zsp_scheduler_s  *sched,
        void                    *args); 
    void (*dtor)(
        struct zsp_actor_base_s *actor);
} zsp_actor_type_t;

typedef struct zsp_actor_base_s {
    // Actor main thread. Actor is-a thread
    zsp_thread_t            thread; // Actor main thread
    zsp_actor_type_t        *type;  // Actor type

    struct zsp_api_s        *api;   // Actor API

} zsp_actor_base_t;

#define zsp_actor_base(actor) ((zsp_actor_base_t *)(actor))

zsp_actor_type_t *zsp_actor_type(zsp_actor_base_t *actor);

#endif /* INCLUDED_ZSP_ACTOR_BASE_H */


#ifndef INCLUDED_HELLO_WORLD_H
#define INCLUDED_HELLO_WORLD_H
#include "zsp_rt.h"

struct pss_top_Entry_actor_s;

typedef struct pss_top_s {

} pss_top_t;

void pss_top_init(
    struct pss_top_Entry_actor_s    *actor,
    pss_top_t                       *root
);

// Component-type struct
typedef struct pss_top_Sub_s {
    zsp_rt_action_t     action;

} pss_top_Sub_t;

void pss_top_Sub_init(
    struct pss_top_Entry_actor_s    *actor,
    pss_top_Sub_t                   *obj);

zsp_rt_task_t *pss_top_Sub_run(
    struct pss_top_Entry_actor_s    *actor,
    pss_top_Sub_t                   *obj);

typedef struct pss_top_Sub_exec_Body_s {
    zsp_rt_task_t                   task;
} pss_top_Sub_exec_body_t;

void pss_top_Sub_exec_body_init(
    struct pss_top_Entry_actor_s    *actor,
    pss_top_Sub_exec_body_t         *obj);

zsp_rt_task_t *pss_top_Sub_exec_body_run(
    struct pss_top_Entry_actor_s    *actor,
    pss_top_Sub_exec_body_t         *obj
);

// Action-type struct
typedef struct pss_top_Entry_s {
    zsp_rt_task_t               task;
    uint32_t                    loop_i;
} pss_top_Entry_t;

void pss_top_Entry_init(
    struct pss_top_Entry_actor_s    *actor,
    pss_top_Entry_t                 *obj);

zsp_rt_task_t *pss_top_Entry_run(
    struct pss_top_Entry_actor_s    *actor,
    pss_top_Entry_t                 *obj);

typedef struct pss_top_Entry_func_s {
    void (*print_f)(const char *s);
} pss_top_Entry_func_t;


typedef struct pss_top_Entry_actor_s {
    zsp_rt_actor_t          actor;
    pss_top_t               root_comp;
    pss_top_Entry_t         root_action;
    pss_top_Entry_func_t    funcs;
} pss_top_Entry_actor_t;

void pss_top_Entry_actor_init(
    pss_top_Entry_actor_t   *actor
);

int pss_top_Entry_actor_runOneTask(
    pss_top_Entry_actor_t   *actor);

void pss_top_Entry_actor_run(
    pss_top_Entry_actor_t   *actor);


#endif /* INCLUDED_HELLO_WORLD_H */


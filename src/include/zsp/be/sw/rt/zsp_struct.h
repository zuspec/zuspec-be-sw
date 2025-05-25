#ifndef INCLUDED_ZSP_STRUCT_H
#define INCLUDED_ZSP_STRUCT_H
#ifdef __cplusplus
extern "C" {
#endif
#include "zsp/be/sw/rt/zsp_object.h"

struct zsp_struct_s;

typedef void (*zsp_solve_exec_f)(struct zsp_actor_s *, struct zsp_struct_s *);

typedef struct zsp_struct_type_s {
    zsp_object_type_t base;

    zsp_solve_exec_f    pre_solve;
    zsp_solve_exec_f    post_solve;

} zsp_struct_type_t;

typedef struct zsp_struct_s {
    zsp_object_t base;

} zsp_struct_t;

#define zsp_struct_call(method, actor, this_p) \
    ((zsp_struct_type_t *)((zsp_object_t *)(this_p))->type)-> method ( \
        (struct zsp_actor_s *)(actor), \
        (struct zsp_struct_s *)(this_p));

#define zsp_struct_pre_solve(actor, this_p) \
    zsp_struct_call(pre_solve, actor, this_p)

#define zsp_struct_post_solve(actor, this_p) \
    zsp_struct_call(post_solve, actor, this_p)

void zsp_struct_init(struct zsp_actor_s *actor, struct zsp_struct_s *this_p);

#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_STRUCT_H */


#ifndef INCLUDED_ZSP_STRUCT_H
#define INCLUDED_ZSP_STRUCT_H
#include <stdarg.h>

#ifdef __cplusplus
extern "C" {
#endif
#include "zsp_object.h"

struct zsp_alloc_s;
struct zsp_struct_s;


typedef void (*zsp_solve_exec_f)(struct zsp_struct_s *);

typedef void (*zsp_struct_init_f)(
    struct zsp_struct_s *self, 
    struct zsp_alloc_s  *alloc,
    va_list             *init);

typedef struct zsp_struct_type_s {
    zsp_object_type_t   base;
    zsp_struct_init_f   init;

    zsp_solve_exec_f    pre_solve;
    zsp_solve_exec_f    post_solve;
    zsp_solve_exec_f    pre_body;

} zsp_struct_type_t;

typedef struct zsp_struct_s {
    zsp_object_t        base;
} zsp_struct_t;

#define zsp_struct(obj) ((zsp_struct_t *)(obj))

#define zsp_struct_call(method, this_p) \
    ((zsp_struct_type_t *)((zsp_object_t *)(this_p))->type)-> method ( \
        (struct zsp_struct_s *)(this_p));

#define zsp_struct_pre_solve(this_p) \
    zsp_struct_call(pre_solve, this_p)

#define zsp_struct_post_solve(this_p) \
    zsp_struct_call(post_solve, this_p)

void zsp_struct_init(struct zsp_alloc_s *alloc, struct zsp_struct_s *this_p);

zsp_struct_type_t *zsp_struct__type(void);

void zsp_struct_type_init(zsp_struct_type_t *t);

typedef void (*zsp_apply_f)(struct zsp_struct_s *this_p, va_list *init);

#define zsp_apply(type, kind, path, val) \
        &zsp_struct_apply_ ## kind, \
        &((type *)0)-> path , \
        val

void zsp_struct_apply_int8(struct zsp_struct_s *this_p, va_list *init);

void zsp_struct_apply_int16(struct zsp_struct_s *this_p, va_list *init);

void zsp_struct_apply_int32(struct zsp_struct_s *this_p, va_list *init);

void zsp_struct_apply_int64(struct zsp_struct_s *this_p, va_list *init);

void zsp_struct_apply_ptr(struct zsp_struct_s *this_p, va_list *init);

void zsp_struct_apply_ref(struct zsp_struct_s *this_p, va_list *init);

void zsp_struct_apply_init(struct zsp_struct_s *this_p, va_list *init);

void zsp_struct_apply(struct zsp_struct_s *this_p, ...);

#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_STRUCT_H */


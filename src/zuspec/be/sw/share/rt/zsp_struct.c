
#include "zsp_alloc.h"
#include "zsp_struct.h"

static void zsp_struct__dtor(struct zsp_struct_s *this_p) {

}

static void zsp_struct__pre_solve(struct zsp_struct_s *this_p) {
    // Pre-solve implementation
}

static void zsp_struct__post_solve(struct zsp_struct_s *this_p) {
    // Pre-solve implementation
}

static void zsp_struct__pre_body(struct zsp_struct_s *this_p) {
    // Pre-solve implementation
}

void zsp_struct_type_init(zsp_struct_type_t *t) {
    zsp_object_type_init((zsp_object_type_t *)t);
    ((zsp_object_type_t *)t)->super = zsp_object__type();
    ((zsp_object_type_t *)t)->name = "zsp_object";
    ((zsp_object_type_t *)t)->dtor = (zsp_dtor_f)&zsp_struct__dtor;
    t->pre_solve = (zsp_solve_exec_f)&zsp_struct__pre_solve;
    t->post_solve = (zsp_solve_exec_f)&zsp_struct__post_solve;
    t->pre_body = (zsp_solve_exec_f)&zsp_struct__pre_body;
}

zsp_struct_type_t *zsp_struct__type(void) {
    static int __init = 0;
    static zsp_struct_type_t __type;
    if (__init == 0) {
        zsp_struct_type_init(&__type);
        __init = 1;
    }

    return &__type;
}

void zsp_struct_init(
    zsp_alloc_t     *alloc, 
    zsp_struct_t    *this_p) {

}

void zsp_struct_apply_init(struct zsp_struct_s *this_p, va_list *init) {
    zsp_apply_f apply;

    if (!init) return;

    while ((apply=va_arg(*init, zsp_apply_f))) {
        apply(this_p, init);
    }
}

void zsp_struct_apply_int8(struct zsp_struct_s *this_p, va_list *init) {
    uint32_t offset = va_arg(*init, uint32_t);
    *((uint8_t *)(((uintptr_t)this_p)+offset)) = va_arg(*init, uint8_t);
}

void zsp_struct_apply_int16(struct zsp_struct_s *this_p, va_list *init) {
    uint32_t offset = va_arg(*init, uint32_t);
    *((uint16_t *)(((uintptr_t)this_p)+offset)) = va_arg(*init, uint16_t);
}

void zsp_struct_apply_int32(struct zsp_struct_s *this_p, va_list *init) {
    uint32_t offset = va_arg(*init, uint32_t);
    *((uint32_t *)(((uintptr_t)this_p)+offset)) = va_arg(*init, uint32_t);
}

void zsp_struct_apply_int64(struct zsp_struct_s *this_p, va_list *init) {
    uint32_t offset = va_arg(*init, uint32_t);
    *((uint64_t *)(((uintptr_t)this_p)+offset)) = va_arg(*init, uint64_t);
}

void zsp_struct_apply_ptr(struct zsp_struct_s *this_p, va_list *init) {
    uint32_t offset = va_arg(*init, uint32_t);
    *((uintptr_t *)(((uintptr_t)this_p)+offset)) = va_arg(*init, uintptr_t);
}

void zsp_struct_apply_ref(struct zsp_struct_s *this_p, va_list *init) {

}

void zsp_struct_apply(struct zsp_struct_s *this_p, ...) {
    va_list ap;
    va_start(ap, this_p);
    zsp_struct_apply_init(this_p, &ap);
    va_end(ap);
}


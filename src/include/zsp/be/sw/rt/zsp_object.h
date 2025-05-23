#ifndef INCLUDED_ZSP_OBJECT_H
#define INCLUDED_ZSP_OBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

struct zsp_object_s;
struct zsp_actor_s;

typedef void (*dtor_f)(struct zsp_actor_s *, struct zsp_object_s *);

typedef struct zsp_object_type_s {
    struct zsp_object_type_s    *super;
    const char                  *name;
    dtor_f                      dtor;
} zsp_object_type_t;

typedef struct zsp_object_s {
    zsp_object_type_t *type;

} zsp_object_t;



#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_OBJECT_H */

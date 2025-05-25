
#include "zsp/be/sw/rt/zsp_object.h"

static void zsp_object__dtor(struct zsp_actor_s *actor, struct zsp_object_s *this_p) {

}

zsp_object_type_t *zsp_object__type(void) {
    static int __init = 0;
    static zsp_object_type_t __type;
    if (__init == 0) {
        ((zsp_object_type_t *)&__type)->super = 0;
        ((zsp_object_type_t *)&__type)->name = "zsp_object";
        ((zsp_object_type_t *)&__type)->dtor = (zsp_dtor_f)&zsp_object__dtor;
        __init = 1;
    }

    return &__type;
}

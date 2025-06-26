#include "zsp/be/sw/rt/zsp_actor.h"
#include "zsp/be/sw/rt/zsp_model.h"

// Focus on solve here...
// 

typedef struct smoke_1_api_s {
    zsp_api_t base;
    int (*add)(int a, int b);
} smoke_1_api_t;

typedef struct smoke_1_s {
    zsp_actor_t base;
} smoke_1_t;

static zsp_frame_t *smoke_1_activity(zsp_thread_t *thread, int32_t idx, va_list *args) {
    // How do we get the actor?
    zsp_frame_t *ret = 0;

    switch (idx) {
        case 0: {
            zsp_actor_t *actor = va_arg(*args, zsp_actor_t *);
            int i, sum = 0;

            for (i=1; i<=16; i++) {
                sum = ((smoke_1_api_t *)actor->base.api)->add(sum, i);
            }
        }
    }
    return ret;
}

static void smoke_1_init(zsp_actor_base_t *actor, zsp_api_t *api) {
    smoke_1_t *self = (smoke_1_t *)actor;

    zsp_actor_init(
        &self->base, 
        api,
        0,
        0);
}

zsp_actor_type_t actor = {
    .name = "smoke_1",
    .size = sizeof(smoke_1_t),
    .init = &smoke_1_init,
    .dtor = 0
};

zsp_actor_type_t **zsp_get_actor_types() {
    static zsp_actor_type_t *types[] = {
        &actor,
        0
    };
    return types;
}

const char **zsp_get_method_types() {
    static const char *method_types[] = {
        "3addiii", 0
    };
    return method_types;
}


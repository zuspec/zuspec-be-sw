#include "zsp/be/sw/rt/zsp_action.h"
#include "zsp/be/sw/rt/zsp_actor.h"
#include "zsp/be/sw/rt/zsp_thread.h"

void zsp_action_init(
    zsp_actor_t *actor, 
    zsp_action_t *this_p) {
    zsp_struct_init(actor, &this_p->base);
    this_p->body = 0;
}

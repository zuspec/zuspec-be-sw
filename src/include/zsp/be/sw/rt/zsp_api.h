
#ifndef INCLUDED_ZSP_API_H
#define INCLUDED_ZSP_API_H
#include "zsp/be/sw/rt/zsp_thread.h"

struct zsp_actor_s;
struct zsp_frame_s;
struct zsp_thread_s;

typedef struct zsp_api_s {
    void (*print)(struct zsp_api_s *self, const char *fmt, ...);

    // zsp_task_func       write64;
    // zsp_task_func       write32;
    // zsp_task_func       write16;
    // zsp_task_func       write8;
    
    // zsp_task_func       read64;
    // zsp_task_func       read32;
    // zsp_task_func       read16;
    // zsp_task_func       read8;

} zsp_api_t;

#endif /* INCLUDED_ZSP_API_H */

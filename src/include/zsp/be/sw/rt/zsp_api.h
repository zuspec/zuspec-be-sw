
#ifndef INCLUDED_ZSP_API_H
#define INCLUDED_ZSP_API_H
#include "zsp/be/sw/rt/zsp_thread.h"

struct zsp_actor_s;
struct zsp_frame_s;
struct zsp_thread_s;

typedef struct zsp_api_s {
    // Built-in methods
    void (*print)(struct zsp_api_s *self, const char *msg);

    // zsp_task_func       write64;
    // zsp_task_func       write32;
    // zsp_task_func       write16;
    // zsp_task_func       write8;
    
    // zsp_task_func       read64;
    // zsp_task_func       read32;
    // zsp_task_func       read16;
    // zsp_task_func       read8;

    // Promise scheme to allow tasks to complete
    // Tasks 

} zsp_api_t;

// Signature is:
// <len>Name
// rtype ptypes
// int func(int) is: 4funcii
// int func(pkg::mytype) is 4funci11pkg::mytype
// int func(int, int) (as a task) is 4funcTiii
// T            - This is a task
// c            - int8
// C            - uint8
// s            - int16
// S            - uint16
// i            - int32
// I            - int64
// u            - uint32
// U            - uint64
// V            - void
// h            - chandle
// <len>Name    - struct
//
// Minimum: V - void function with no arguments
// Vi - void function with one int argument

// May be able to do something similar for struct layout

// A task function accepts 'thread' as an unspecified first
// parameter. It passes its return value by calling zsp_thread_return()
// The implementation is expected to adhere to the coroutine protocol


#endif /* INCLUDED_ZSP_API_H */

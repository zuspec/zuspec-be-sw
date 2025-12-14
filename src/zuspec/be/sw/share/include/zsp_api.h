
#ifndef INCLUDED_ZSP_API_H
#define INCLUDED_ZSP_API_H
#include "zsp_thread.h"

struct zsp_frame_s;
struct zsp_thread_s;

typedef enum {
    MSG_LEVEL_LOW,
    MSG_LEVEL_MED,
    MSG_LEVEL_HIGH
} msg_level_e;

typedef struct zsp_api_s {
    // Built-in methods
    void (*print)(struct zsp_api_s *self, const char *msg);
    void (*message)(struct zsp_api_s *self, msg_level_e level, const char *msg);

} zsp_api_t;

// Signature is:
// <len>Name
// rtype ptypes
// int func(int) is: 4funcii
// int func(pkg::mytype) is 4funci11pkg::mytype
// int func(int, int) (as a task) is 4funcTiii
// T            - This is a task
// b            - bool
// c            - int8
// C            - uint8
// h            - int16
// H            - uint16
// i            - int32
// I            - uint32
// l            - int64
// L            - uint64
// s            - string
// V            - void
// h            - chandle
// S<len>Name   - struct
// E<len>Name   - enum
//
// Minimum: V - void function with no arguments
// Vi - void function with one int argument

// May be able to do something similar for struct layout

// A task function accepts 'thread' as an unspecified first
// parameter. It passes its return value by calling zsp_thread_return()
// The implementation is expected to adhere to the coroutine protocol


#endif /* INCLUDED_ZSP_API_H */

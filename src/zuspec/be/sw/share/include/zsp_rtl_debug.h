/**
 * zsp_rtl_debug.h  —  debug support types and macros for zuspec-be-rtl
 *
 * Included by generated C when compiled with -DZS_DEBUG.
 * Provides:
 *   ZspLoc_t         – Python source location (file, line)
 *   ZspCoroFrame_t   – coroutine stack frame node (linked list)
 *   zsp_coro_top     – thread-local head of the coroutine frame stack
 *   ZS_LOC()         – update current frame's location in-place
 *   zsp_push_frame() – push a coroutine frame at entry
 *   zsp_pop_frame()  – pop a coroutine frame at exit
 */
#ifndef ZSP_RTL_DEBUG_H
#define ZSP_RTL_DEBUG_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/* -----------------------------------------------------------------------
 * Source location — Python-side filename and line number carried in each
 * generated coroutine struct so GDB can always find the true origin.
 * ----------------------------------------------------------------------- */
typedef struct ZspLoc {
    const char *file;
    int32_t     line;
} ZspLoc_t;

/* -----------------------------------------------------------------------
 * Coroutine frame — a singly-linked list node pushed onto the per-thread
 * stack zsp_coro_top whenever a coroutine is entered.  Each node holds a
 * mutable ZspLoc that is updated at every suspension point via ZS_LOC().
 * ----------------------------------------------------------------------- */
typedef struct ZspCoroFrame {
    const char         *co_name;    /* coroutine / action name */
    ZspLoc_t            loc;        /* current Python source location   */
    struct ZspCoroFrame *prev;      /* link to caller's frame            */
} ZspCoroFrame_t;

/* Thread-local head of the coroutine frame stack.
 * Defined once in zsp_rtl_debug.c. */
extern _Thread_local ZspCoroFrame_t *zsp_coro_top;

/* -----------------------------------------------------------------------
 * Inline helpers used by generated code.
 * ----------------------------------------------------------------------- */

/**
 * ZS_LOC(frame_ptr, file_str, line_int)
 * Update the Python source location inside an already-pushed frame.
 * Call this at each suspension point / statement boundary.
 */
#define ZS_LOC(frame, f, l) \
    do { (frame)->loc.file = (f); (frame)->loc.line = (l); } while(0)

/**
 * zsp_push_frame(fp, name, file, line)
 * Initialise *fp and push it onto the thread-local coroutine stack.
 */
static inline void zsp_push_frame(ZspCoroFrame_t *fp,
                                   const char     *name,
                                   const char     *file,
                                   int32_t         line)
{
    fp->co_name  = name;
    fp->loc.file = file;
    fp->loc.line = line;
    fp->prev     = zsp_coro_top;
    zsp_coro_top = fp;
}

/**
 * zsp_pop_frame()
 * Pop the top frame from the coroutine stack.
 */
static inline void zsp_pop_frame(void)
{
    if (zsp_coro_top)
        zsp_coro_top = zsp_coro_top->prev;
}

/* -----------------------------------------------------------------------
 * Assertion with Python source location in the message.
 * ----------------------------------------------------------------------- */
#ifdef ZS_DEBUG
#  include <stdio.h>
#  include <stdlib.h>
#  define ZSP_ASSERT(cond, msg)                                         \
     do {                                                               \
         if (!(cond)) {                                                 \
             const char *_f = zsp_coro_top ? zsp_coro_top->loc.file    \
                                           : "<unknown>";               \
             int32_t _l     = zsp_coro_top ? zsp_coro_top->loc.line    \
                                           : 0;                         \
             fprintf(stderr, "%s:%d: ZSP assertion failed: %s\n",      \
                     _f, _l, (msg));                                    \
             abort();                                                   \
         }                                                              \
     } while(0)
#else
#  define ZSP_ASSERT(cond, msg) ((void)(cond))
#endif

/* Helper declared in zsp_rtl_debug.c — prints the full coro stack */
void zsp_print_coro_stack(void);

#ifdef __cplusplus
}
#endif

#endif /* ZSP_RTL_DEBUG_H */

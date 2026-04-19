"""C runtime: zdc_spawn — fire-and-forget coroutine launch."""

HEADER = r"""
#ifndef ZDC_SPAWN_H
#define ZDC_SPAWN_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "zdc_coro.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * zdc_spawn_handle_t — opaque handle to a spawned coroutine.
 *
 * The caller of zdc_spawn() receives a handle.  The spawned coroutine runs
 * independently.  The caller may call zdc_spawn_join() to wait for it to
 * complete, or simply ignore the handle if fire-and-forget semantics are
 * desired.
 */
typedef struct {
    zdc_coro_t *coro;   /**< The spawned coroutine (NULL after it finishes) */
    bool        done;   /**< True after the spawned coroutine has returned */
    zdc_coro_t *joiner; /**< Coroutine waiting in zdc_spawn_join() */
} zdc_spawn_handle_t;

/**
 * zdc_spawn() — launch *fn* as a new independent coroutine.
 *
 * @param handle   Caller-allocated handle; initialised by this function.
 * @param fn       Coroutine entry function: void fn(void *arg, zdc_coro_t *self)
 * @param arg      Opaque argument passed verbatim to fn.
 * @param stack    Caller-allocated stack buffer for the new coroutine.
 * @param stack_sz Size of the stack buffer in bytes.
 *
 * The spawned coroutine is immediately scheduled.  The current coroutine is
 * *not* suspended — zdc_spawn() returns synchronously.
 */
void zdc_spawn(
    zdc_spawn_handle_t *handle,
    void              (*fn)(void *arg, zdc_coro_t *self),
    void               *arg,
    uint8_t            *stack,
    size_t              stack_sz);

/**
 * ZDC_SPAWN_JOIN(handle, frame, next_label) — await spawned coroutine.
 *
 * Suspends until the spawned coroutine finishes.  Use like
 * ZDC_COMPLETION_AWAIT for in-line coroutine suspension.
 */
#define ZDC_SPAWN_JOIN(handle, frame, next_label)               \
    do {                                                        \
        if (!(handle)->done) {                                  \
            (handle)->joiner = (frame)->coro;                   \
            (frame)->resume_label = &&next_label;               \
            return;                                             \
        }                                                       \
        next_label:;                                            \
    } while (0)

#ifdef __cplusplus
}
#endif

#endif /* ZDC_SPAWN_H */
""".lstrip()

SOURCE = r"""
#include "zdc_spawn.h"
#include <string.h>

typedef struct {
    void              (*user_fn)(void *arg, zdc_coro_t *self);
    void               *user_arg;
    zdc_spawn_handle_t *handle;
} _zdc_spawn_wrapper_arg_t;

static void _spawn_wrapper(void *raw_arg, zdc_coro_t *self) {
    _zdc_spawn_wrapper_arg_t *wa = (_zdc_spawn_wrapper_arg_t *)raw_arg;
    wa->user_fn(wa->user_arg, self);
    /* Signal completion */
    wa->handle->done = true;
    wa->handle->coro = NULL;
    if (wa->handle->joiner) {
        zdc_coro_schedule(wa->handle->joiner);
        wa->handle->joiner = NULL;
    }
}

void zdc_spawn(
    zdc_spawn_handle_t *handle,
    void              (*fn)(void *arg, zdc_coro_t *self),
    void               *arg,
    uint8_t            *stack,
    size_t              stack_sz)
{
    handle->done   = false;
    handle->joiner = NULL;

    /* Reuse the stack prefix for the wrapper arg (simple approach). */
    _zdc_spawn_wrapper_arg_t *wa = (_zdc_spawn_wrapper_arg_t *)(void *)stack;
    wa->user_fn  = fn;
    wa->user_arg = arg;
    wa->handle   = handle;

    uint8_t    *coro_stack = stack + sizeof(_zdc_spawn_wrapper_arg_t);
    size_t      coro_stack_sz = stack_sz - sizeof(_zdc_spawn_wrapper_arg_t);

    handle->coro = zdc_coro_create(_spawn_wrapper, wa, coro_stack, coro_stack_sz);
    zdc_coro_schedule(handle->coro);
}
""".lstrip()

"""C runtime: zdc_completion — one-shot result synchronization."""

HEADER = r"""
#ifndef ZDC_COMPLETION_H
#define ZDC_COMPLETION_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "zdc_coro.h"   /* zdc_coro_t, zdc_coro_yield */

#ifdef __cplusplus
extern "C" {
#endif

/* Maximum inline payload size in bytes (larger payloads use a pointer). */
#define ZDC_COMPLETION_MAX_INLINE 64

/**
 * zdc_completion_t — one-shot result token.
 *
 * Created by the export implementation; passed (via a struct field or queue)
 * to the coroutine that calls zdc_completion_await().
 * zdc_completion_set() must be called exactly once; zdc_completion_await()
 * must be called exactly once.
 */
typedef struct {
    bool          set;                              /**< True after set() */
    zdc_coro_t   *waiter;                           /**< Suspended coroutine (if any) */
    uint8_t       payload[ZDC_COMPLETION_MAX_INLINE]; /**< Inline result storage */
    size_t        payload_size;                     /**< Size of stored payload */
} zdc_completion_t;

/** Initialise a completion token to the unset state. */
static inline void zdc_completion_init(zdc_completion_t *c) {
    c->set          = false;
    c->waiter       = NULL;
    c->payload_size = 0;
}

/**
 * zdc_completion_set() — called from the responder side (non-blocking).
 *
 * Stores *value* (of *size* bytes) and marks the completion as set.
 * If a coroutine is already suspended on zdc_completion_await(), it is
 * rescheduled immediately.
 */
void zdc_completion_set(zdc_completion_t *c, const void *value, size_t size);

/**
 * ZDC_COMPLETION_AWAIT(c, out, size, frame, next_label) — coroutine macro.
 *
 * Checks whether the completion is already set.  If not, stores the coroutine
 * pointer as the waiter and suspends.  After resumption (or if already set),
 * copies the payload into *out*.
 *
 * Usage inside a coroutine continuation switch arm:
 *   ZDC_COMPLETION_AWAIT(&req->done, &result, sizeof(result), frame, L_after);
 *   L_after:;
 */
#define ZDC_COMPLETION_AWAIT(c, out, size, frame, next_label)   \
    do {                                                         \
        if (!(c)->set) {                                         \
            (c)->waiter = (frame)->coro;                         \
            (frame)->resume_label = &&next_label;                \
            return;  /* suspend */                               \
        }                                                        \
        next_label:;                                             \
        if ((out) && (size) <= ZDC_COMPLETION_MAX_INLINE)        \
            __builtin_memcpy((out), (c)->payload, (size));       \
    } while (0)

#ifdef __cplusplus
}
#endif

#endif /* ZDC_COMPLETION_H */
""".lstrip()

SOURCE = r"""
#include "zdc_completion.h"
#include <string.h>

void zdc_completion_set(zdc_completion_t *c, const void *value, size_t size) {
    if (c->set) {
        /* Violation — double-set; in simulation just ignore the second call */
        return;
    }
    c->set = true;
    if (value && size > 0 && size <= ZDC_COMPLETION_MAX_INLINE) {
        memcpy(c->payload, value, size);
        c->payload_size = size;
    }
    /* Wake the waiting coroutine (if any) via the scheduler */
    if (c->waiter) {
        zdc_coro_schedule(c->waiter);
        c->waiter = NULL;
    }
}
""".lstrip()

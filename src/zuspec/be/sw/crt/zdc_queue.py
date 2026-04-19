"""C runtime: zdc_queue — fixed-depth ring-buffer FIFO."""

HEADER = r"""
#ifndef ZDC_QUEUE_H
#define ZDC_QUEUE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "zdc_coro.h"

#ifdef __cplusplus
extern "C" {
#endif

#ifndef ZDC_MAX_WAITERS
#  define ZDC_MAX_WAITERS 16
#endif

/**
 * zdc_queue_t — fixed-depth ring-buffer FIFO.
 *
 * buf must point to a statically allocated byte array of size
 * depth * elem_size.  Use ZDC_QUEUE_DECL / ZDC_QUEUE_INIT for convenience.
 */
typedef struct {
    uint8_t    *buf;                          /**< Backing storage */
    size_t      elem_size;                    /**< Size of one element in bytes */
    int         depth;                        /**< Maximum number of entries */
    int         head;                         /**< Read index */
    int         tail;                         /**< Write index */
    int         count;                        /**< Current occupancy */
    zdc_coro_t *put_waiters[ZDC_MAX_WAITERS]; /**< Coroutines blocked on put */
    int         put_waiter_count;
    zdc_coro_t *get_waiters[ZDC_MAX_WAITERS]; /**< Coroutines blocked on get */
    int         get_waiter_count;
} zdc_queue_t;

/**
 * ZDC_QUEUE_DECL(name, T, depth) — declare a queue and its backing storage.
 *
 *   ZDC_QUEUE_DECL(my_q, uint32_t, 8);
 *   ZDC_QUEUE_INIT(&my_q, sizeof(uint32_t), 8);
 */
#define ZDC_QUEUE_DECL(name, T, _depth)   \
    uint8_t     name##_buf[(_depth) * sizeof(T)]; \
    zdc_queue_t name

#define ZDC_QUEUE_INIT(q, _elem_size, _depth)   \
    do {                                         \
        (q)->buf            = (q##_buf);         \
        (q)->elem_size      = (_elem_size);      \
        (q)->depth          = (_depth);          \
        (q)->head           = 0;                 \
        (q)->tail           = 0;                 \
        (q)->count          = 0;                 \
        (q)->put_waiter_count = 0;               \
        (q)->get_waiter_count = 0;               \
    } while (0)

/** True if queue is full (no space for another put). */
static inline bool zdc_queue_full(const zdc_queue_t *q) {
    return q->count >= q->depth;
}

/** True if queue is empty (no item available for get). */
static inline bool zdc_queue_empty(const zdc_queue_t *q) {
    return q->count == 0;
}

/** Current number of items in the queue. */
static inline int zdc_queue_size(const zdc_queue_t *q) {
    return q->count;
}

/**
 * zdc_queue_put() — enqueue one item (suspends if full).
 *
 * Must be called inside a coroutine continuation; uses the same
 * suspend/resume mechanism as the completion token.
 *
 * ZDC_QUEUE_PUT(q, &item, sizeof(item), frame, next_label) — macro form.
 */
void zdc_queue_put(zdc_queue_t *q, const void *item, size_t size);

/**
 * zdc_queue_get() — dequeue one item (suspends if empty).
 *
 * ZDC_QUEUE_GET(q, out, sizeof(*out), frame, next_label) — macro form.
 */
void zdc_queue_get(zdc_queue_t *q, void *out, size_t size);

/* Coroutine-aware macro wrappers ----------------------------------------- */

#define ZDC_QUEUE_PUT(q, item_ptr, size, frame, next_label)      \
    do {                                                          \
        if (zdc_queue_full(q)) {                                  \
            (q)->put_waiters[(q)->put_waiter_count++] = (frame)->coro; \
            (frame)->resume_label = &&next_label;                 \
            return;                                               \
        }                                                         \
        next_label:;                                              \
        zdc_queue_put_nowait(q, item_ptr, size);                  \
    } while (0)

#define ZDC_QUEUE_GET(q, out_ptr, size, frame, next_label)        \
    do {                                                          \
        if (zdc_queue_empty(q)) {                                 \
            (q)->get_waiters[(q)->get_waiter_count++] = (frame)->coro; \
            (frame)->resume_label = &&next_label;                 \
            return;                                               \
        }                                                         \
        next_label:;                                              \
        zdc_queue_get_nowait(q, out_ptr, size);                   \
    } while (0)

/** Non-blocking put (caller must check !full first). */
void zdc_queue_put_nowait(zdc_queue_t *q, const void *item, size_t size);

/** Non-blocking get (caller must check !empty first). */
void zdc_queue_get_nowait(zdc_queue_t *q, void *out, size_t size);

#ifdef __cplusplus
}
#endif

#endif /* ZDC_QUEUE_H */
""".lstrip()

SOURCE = r"""
#include "zdc_queue.h"
#include <string.h>

void zdc_queue_put_nowait(zdc_queue_t *q, const void *item, size_t size) {
    uint8_t *slot = q->buf + q->tail * q->elem_size;
    memcpy(slot, item, size < q->elem_size ? size : q->elem_size);
    q->tail = (q->tail + 1) % q->depth;
    q->count++;
    /* Wake a blocked getter if any */
    if (q->get_waiter_count > 0) {
        zdc_coro_t *waiter = q->get_waiters[0];
        for (int i = 1; i < q->get_waiter_count; i++)
            q->get_waiters[i-1] = q->get_waiters[i];
        q->get_waiter_count--;
        zdc_coro_schedule(waiter);
    }
}

void zdc_queue_get_nowait(zdc_queue_t *q, void *out, size_t size) {
    uint8_t *slot = q->buf + q->head * q->elem_size;
    memcpy(out, slot, size < q->elem_size ? size : q->elem_size);
    q->head = (q->head + 1) % q->depth;
    q->count--;
    /* Wake a blocked putter if any */
    if (q->put_waiter_count > 0) {
        zdc_coro_t *waiter = q->put_waiters[0];
        for (int i = 1; i < q->put_waiter_count; i++)
            q->put_waiters[i-1] = q->put_waiters[i];
        q->put_waiter_count--;
        zdc_coro_schedule(waiter);
    }
}

void zdc_queue_put(zdc_queue_t *q, const void *item, size_t size) {
    /* Blocking put — caller is responsible for using the macro form in coros */
    while (zdc_queue_full(q)) { /* spin (should not happen in coro context) */ }
    zdc_queue_put_nowait(q, item, size);
}

void zdc_queue_get(zdc_queue_t *q, void *out, size_t size) {
    /* Blocking get — caller is responsible for using the macro form in coros */
    while (zdc_queue_empty(q)) { /* spin (should not happen in coro context) */ }
    zdc_queue_get_nowait(q, out, size);
}
""".lstrip()

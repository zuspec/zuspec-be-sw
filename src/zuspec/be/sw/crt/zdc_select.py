"""C runtime: zdc_select — wait for the first of several queues to have data."""

HEADER = r"""
#ifndef ZDC_SELECT_H
#define ZDC_SELECT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "zdc_queue.h"

#ifdef __cplusplus
extern "C" {
#endif

#ifndef ZDC_SELECT_MAX_BRANCHES
#  define ZDC_SELECT_MAX_BRANCHES 16
#endif

/**
 * zdc_select_t — state for a multi-queue select.
 *
 * Declare one of these on the stack, fill branches[], set n_branches, then
 * call ZDC_SELECT_WAIT(sel, frame, next_label).  After resumption, check
 * sel.ready_idx for the index of the branch that fired.
 */
typedef struct {
    zdc_queue_t *queues[ZDC_SELECT_MAX_BRANCHES]; /**< Queues to watch */
    int          n_branches;                      /**< Number of queues */
    int          ready_idx;                       /**< Index of ready queue (-1 = none) */
    zdc_coro_t  *waiter;                          /**< Suspended coroutine */
} zdc_select_t;

/**
 * ZDC_SELECT_WAIT(sel, frame, next_label) — suspend until any branch is ready.
 *
 * After resumption, sel->ready_idx contains the index of the first non-empty
 * queue.  The item is NOT dequeued automatically; the caller should
 * ZDC_QUEUE_GET on queues[ready_idx].
 */
#define ZDC_SELECT_WAIT(sel, frame, next_label)                       \
    do {                                                              \
        (sel)->ready_idx = -1;                                        \
        /* Quick scan for an already-ready branch */                  \
        for (int _i = 0; _i < (sel)->n_branches; _i++) {             \
            if (!zdc_queue_empty((sel)->queues[_i])) {                \
                (sel)->ready_idx = _i;                                \
                break;                                                \
            }                                                         \
        }                                                             \
        if ((sel)->ready_idx < 0) {                                   \
            /* Register as waiter on each queue */                    \
            (sel)->waiter = (frame)->coro;                            \
            zdc_select_register_waiter(sel);                          \
            (frame)->resume_label = &&next_label;                     \
            return;                                                   \
        }                                                             \
        next_label:;                                                  \
    } while (0)

/** Register *sel->waiter* on each queue's get-waiter list. */
void zdc_select_register_waiter(zdc_select_t *sel);

/** Called by a queue's put routine when it detects pending select waiters. */
void zdc_select_notify(zdc_select_t *sel, int ready_idx);

#ifdef __cplusplus
}
#endif

#endif /* ZDC_SELECT_H */
""".lstrip()

SOURCE = r"""
#include "zdc_select.h"

/* We embed the zdc_select_t pointer in the queue waiter list using a sentinel
   scheme.  The simple approach here is to poll: register an ordinary coro as
   the waiter on every branch queue, and on resume do a linear scan. */

void zdc_select_register_waiter(zdc_select_t *sel) {
    for (int i = 0; i < sel->n_branches; i++) {
        zdc_queue_t *q = sel->queues[i];
        if (q->get_waiter_count < ZDC_MAX_WAITERS)
            q->get_waiters[q->get_waiter_count++] = sel->waiter;
    }
}

void zdc_select_notify(zdc_select_t *sel, int ready_idx) {
    if (sel->ready_idx >= 0) return;  /* already notified */
    sel->ready_idx = ready_idx;
    /* Remove our waiter from all other queues */
    for (int i = 0; i < sel->n_branches; i++) {
        if (i == ready_idx) continue;
        zdc_queue_t *q = sel->queues[i];
        for (int w = 0; w < q->get_waiter_count; w++) {
            if (q->get_waiters[w] == sel->waiter) {
                for (int j = w + 1; j < q->get_waiter_count; j++)
                    q->get_waiters[j-1] = q->get_waiters[j];
                q->get_waiter_count--;
                break;
            }
        }
    }
    if (sel->waiter) {
        zdc_coro_schedule(sel->waiter);
        sel->waiter = NULL;
    }
}
""".lstrip()

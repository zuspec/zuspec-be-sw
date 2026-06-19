/* zsp_bridge — see zsp_bridge.h. */
#include <stdlib.h>
#include <stdarg.h>
#include "zsp_bridge.h"
#include "zsp_alloc.h"

#define ZSP_BRIDGE_MAX_REQ 64

typedef struct {
    int           in_use;
    int           fn_id;
    int           argc;
    int64_t       argv[ZSP_BRIDGE_MAX_ARGS];
    int64_t       ret;
    zsp_thread_t *thread;
} zsp_bridge_req_t;

struct zsp_bridge_s {
    zsp_alloc_t      alloc;
    zsp_timebase_t   tb;
    zsp_bridge_req_t req[ZSP_BRIDGE_MAX_REQ];
    int              pending[ZSP_BRIDGE_MAX_REQ];   /* FIFO of posted req ids */
    int              pend_head, pend_tail, pend_count;
    int64_t          solve_argv[ZSP_BRIDGE_MAX_ARGS]; /* synchronous-call args */
    int              solve_argc;
};

/* Single active bridge — the coroutine-side helpers reach it without threading
 * a handle through every generated call. */
static zsp_bridge_t *g_bridge = NULL;

/* Minimal svdpi surface (resolved from the simulator runtime at load time via
 * --export-dynamic) so we can set the SV scope before invoking an export. */
typedef void *svScope;
extern svScope svGetScope(void);
extern svScope svSetScope(const svScope);
static svScope g_svscope = NULL;

void zsp_bridge_capture_scope(void) { g_svscope = svGetScope(); }

zsp_bridge_t *zsp_bridge_create(void) {
    zsp_bridge_t *b = (zsp_bridge_t *)calloc(1, sizeof(*b));
    if (!b) return NULL;
    zsp_alloc_malloc_init(&b->alloc);
    zsp_timebase_init(&b->tb, &b->alloc, ZSP_TIME_NS);
    g_bridge = b;
    return b;
}

void zsp_bridge_destroy(zsp_bridge_t *b) {
    if (!b) return;
    if (g_bridge == b) g_bridge = NULL;
    zsp_timebase_destroy(&b->tb);
    free(b);
}

void zsp_bridge_spawn(zsp_bridge_t *b, int action_id, uint64_t seed) {
    g_bridge = b;
    zsp_scenario_spawn(&b->tb, action_id, seed);
}

void zsp_bridge_run(zsp_bridge_t *b) {
    g_bridge = b;
    while (zsp_timebase_run(&b->tb)) { }
}

int zsp_bridge_done(zsp_bridge_t *b) {
    return !zsp_timebase_has_pending(&b->tb) && b->pend_count == 0;
}

int zsp_bridge_next_request(zsp_bridge_t *b, int *req_id, int *fn_id) {
    if (b->pend_count == 0) return 0;
    int rid = b->pending[b->pend_head];
    b->pend_head = (b->pend_head + 1) % ZSP_BRIDGE_MAX_REQ;
    b->pend_count--;
    if (req_id) *req_id = rid;
    if (fn_id)  *fn_id  = b->req[rid].fn_id;
    return 1;
}

int zsp_bridge_argc(zsp_bridge_t *b, int req_id) {
    return b->req[req_id].argc;
}

int64_t zsp_bridge_arg(zsp_bridge_t *b, int req_id, int idx) {
    if (idx < 0 || idx >= b->req[req_id].argc) return 0;
    return b->req[req_id].argv[idx];
}

void zsp_bridge_complete(zsp_bridge_t *b, int req_id, int64_t ret) {
    zsp_bridge_req_t *r = &b->req[req_id];
    r->ret = ret;
    if (r->thread) zsp_timebase_schedule(&b->tb, r->thread);   /* re-wake */
}

/* --- coroutine-side helpers (use g_bridge) --------------------------- */
int zsp_scenario_post_import(zsp_thread_t *thread, int fn_id, int argc, ...) {
    zsp_bridge_t *b = g_bridge;
    int rid = -1, i;
    for (i = 0; i < ZSP_BRIDGE_MAX_REQ; i++)
        if (!b->req[i].in_use) { rid = i; break; }
    /* (no free slot is a fatal misconfiguration; bounded scenario fan-out) */
    zsp_bridge_req_t *r = &b->req[rid];
    r->in_use = 1;
    r->fn_id  = fn_id;
    r->argc   = (argc > ZSP_BRIDGE_MAX_ARGS) ? ZSP_BRIDGE_MAX_ARGS : argc;
    r->ret    = 0;
    r->thread = thread;
    va_list ap;
    va_start(ap, argc);
    for (i = 0; i < r->argc; i++) r->argv[i] = va_arg(ap, int64_t);
    va_end(ap);
    /* suspend: leave the ready queue until completed */
    thread->flags |= ZSP_THREAD_FLAGS_BLOCKED;
    b->pending[b->pend_tail] = rid;
    b->pend_tail = (b->pend_tail + 1) % ZSP_BRIDGE_MAX_REQ;
    b->pend_count++;
    return rid;
}

int64_t zsp_scenario_import_ret(int req_id) {
    zsp_bridge_req_t *r = &g_bridge->req[req_id];
    int64_t v = r->ret;
    r->in_use = 0;
    return v;
}

void zsp_scenario_import_done(int req_id) {
    g_bridge->req[req_id].in_use = 0;
}

int64_t zsp_scenario_call_solve(int fn_id, int argc, ...) {
    zsp_bridge_t *b = g_bridge;
    int i;
    b->solve_argc = (argc > ZSP_BRIDGE_MAX_ARGS) ? ZSP_BRIDGE_MAX_ARGS : argc;
    va_list ap;
    va_start(ap, argc);
    for (i = 0; i < b->solve_argc; i++) b->solve_argv[i] = va_arg(ap, int64_t);
    va_end(ap);
    if (g_svscope) svSetScope(g_svscope);     /* SV scope for the export call */
    return zsp_bridge_call_function(fn_id);   /* synchronous re-entry into SV */
}

int64_t zsp_bridge_solve_arg(zsp_bridge_t *b, int idx) {
    if (idx < 0 || idx >= b->solve_argc) return 0;
    return b->solve_argv[idx];
}

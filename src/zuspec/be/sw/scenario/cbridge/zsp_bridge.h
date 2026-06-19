/*
 * zsp_bridge — host-driven driver around a generated PSS scenario.
 *
 * The generated scenario is a set of non-blocking `zsp_timebase` coroutines.
 * The bridge owns the timebase and exposes a small, SCENARIO-INDEPENDENT C ABI
 * that a host (a SystemVerilog testbench over DPI, or a plain C main) drives:
 *
 *     b = zsp_bridge_create();
 *     zsp_bridge_spawn(b, action_id, seed);
 *     for (;;) {
 *         zsp_bridge_run(b);                       // run the C scheduler
 *         int rid, fid;
 *         if (zsp_bridge_next_request(b, &rid, &fid)) {
 *             // service a blocking import: read args, run the host task,
 *             int64_t ret = host_call(fid, b, rid);
 *             zsp_bridge_complete(b, rid, ret);    // re-wake the coroutine
 *         } else if (zsp_bridge_done(b)) break;
 *     }
 *     zsp_bridge_destroy(b);
 *
 * The ABI is deliberately generic (spawn by integer action id, opaque handle,
 * int64 args) so the scenario `.so` can be rebuilt without changing the
 * host/SV side.
 *
 * Solving (dv-solve) is linked into the same object and runs entirely C-side.
 */
#ifndef ZSP_BRIDGE_H
#define ZSP_BRIDGE_H

#include <stdint.h>
#include "zsp_timebase.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ZSP_BRIDGE_MAX_ARGS 8

typedef struct zsp_bridge_s zsp_bridge_t;

/* Provided by the GENERATED scenario object: spawn the root coroutine for the
 * given export-action id, seeding the root LCG. */
extern void zsp_scenario_spawn(zsp_timebase_t *tb, int action_id, uint64_t seed);

/* --- host (SV/C) facing ABI ------------------------------------------- */
zsp_bridge_t *zsp_bridge_create(void);
void          zsp_bridge_destroy(zsp_bridge_t *b);
void          zsp_bridge_spawn(zsp_bridge_t *b, int action_id, uint64_t seed);
void          zsp_bridge_run(zsp_bridge_t *b);
int           zsp_bridge_done(zsp_bridge_t *b);

/* Pending blocking-import requests. next_request pops one (1 if returned). */
int           zsp_bridge_next_request(zsp_bridge_t *b, int *req_id, int *fn_id);
int           zsp_bridge_argc(zsp_bridge_t *b, int req_id);
int64_t       zsp_bridge_arg(zsp_bridge_t *b, int req_id, int idx);
void          zsp_bridge_complete(zsp_bridge_t *b, int req_id, int64_t ret);

/* --- coroutine (generated scenario) facing helpers -------------------- */
/* Post a blocking import request and suspend the calling coroutine; returns a
 * request id. Variadic args are int64 (scalar marshalling). */
int           zsp_scenario_post_import(zsp_thread_t *thread, int fn_id,
                                       int argc, ...);
/* Return value of a completed import (solve), then release the slot. */
int64_t       zsp_scenario_import_ret(int req_id);
/* Release a completed import slot (void/target import — no return). */
void          zsp_scenario_import_done(int req_id);

/* Non-blocking (solve) import: call the host SYNCHRONOUSLY (no suspend) and
 * return its value. The coroutine stays running; the C side re-enters SV via
 * the `export "DPI-C"` zsp_bridge_call_function. */
int64_t       zsp_scenario_call_solve(int fn_id, int argc, ...);
/* SV reads a synchronous-call argument by index. */
int64_t       zsp_bridge_solve_arg(zsp_bridge_t *b, int idx);
/* Implemented in SV (export "DPI-C") — dispatches fn_id to import_api_if. */
extern int64_t zsp_bridge_call_function(int fn_id);
/* Capture the current SV scope (call from SV, context import) so solve-import
 * re-entry can svSetScope before invoking the export. */
void          zsp_bridge_capture_scope(void);

#ifdef __cplusplus
}
#endif

#endif /* ZSP_BRIDGE_H */

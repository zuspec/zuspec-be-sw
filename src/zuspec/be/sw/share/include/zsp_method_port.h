#ifndef INCLUDED_ZSP_METHOD_PORT_H
#define INCLUDED_ZSP_METHOD_PORT_H

/*============================================================================
 * Method Port Runtime Support
 *
 * A method port binding associates an implementation pointer with one
 * function pointer per protocol method.  Concrete structs are generated
 * per protocol by the Zuspec backend; this header provides the common
 * call macros used at call sites.
 *
 * Generated struct pattern (one per protocol, e.g. MemIF):
 *
 *   typedef struct {
 *       void        *impl;
 *       zsp_frame_t *(*transport)(void *impl, zsp_thread_t *,
 *                                 MemTransaction_t *, zsp_frame_t **);
 *   } MemIF_t;
 *
 * Export self-binding in component init:
 *   self->mem_export.impl      = self;
 *   self->mem_export.transport = DRAMModel_transport_task;
 *
 * Port forwarding in parent init (after __bind__ elaboration):
 *   child->mem.impl      = target->mem_export.impl;
 *   child->mem.transport = target->mem_export.transport;
 *============================================================================*/

#include "zsp_timebase.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Call a bound async method port.
 * port_ptr  — pointer to the protocol struct (e.g. MemIF_t *)
 * method    — method field name within the struct
 * ret_pp    — zsp_frame_t ** for coroutine continuation
 * ...       — additional method arguments
 *
 * Returns the zsp_frame_t * that the calling coroutine must propagate.
 */
#define ZSP_PORT_CALL(port_ptr, method, ret_pp, ...) \
    (port_ptr)->method((port_ptr)->impl, thread, ##__VA_ARGS__, (ret_pp))

/*
 * Call a bound synchronous method port (no coroutine frame needed).
 */
#define ZSP_PORT_CALL_SYNC(port_ptr, method, ...) \
    (port_ptr)->method((port_ptr)->impl, ##__VA_ARGS__)

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_METHOD_PORT_H */

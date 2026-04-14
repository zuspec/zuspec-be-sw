/* zsp_rtl_harness.h — Zuspec RTL Tier-2 (behavioral) simulation harness.
 *
 * Included by generated *_ctypes.py via the sim_run / sim_step wrappers.
 * The Foo_sim_run() function is emitted by CEmitPass when behavioral
 * processes are present; this header just declares the shared time type.
 *
 * No external dependencies beyond zsp_rtl.h.
 */
#ifndef _ZSP_RTL_HARNESS_H
#define _ZSP_RTL_HARNESS_H

#include "zsp_rtl.h"

/* Picosecond timestamp type (uint64_t covers ~10 years @ 1 GHz). */
typedef uint64_t zsp_ps_t;

#endif /* _ZSP_RTL_HARNESS_H */

"""C runtime: zdc_runtime — umbrella header that includes everything."""

HEADER = r"""
#ifndef ZDC_RUNTIME_H
#define ZDC_RUNTIME_H

/**
 * zdc_runtime.h — convenience umbrella header.
 *
 * Include this single header to pull in all zuspec-be-sw C runtime support:
 *   - zdc_completion (one-shot result tokens)
 *   - zdc_queue      (blocking ring-buffer FIFOs)
 *   - zdc_spawn      (coroutine launch + join)
 *   - zdc_select     (multi-queue ready-wait)
 */

#include "zdc_completion.h"
#include "zdc_queue.h"
#include "zdc_spawn.h"
#include "zdc_select.h"

#endif /* ZDC_RUNTIME_H */
""".lstrip()

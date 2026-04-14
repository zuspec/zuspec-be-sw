/* zsp_rtl.h — Zuspec RTL compiled-C runtime (Tier 0 / Tier 1)
 *
 * No external dependencies beyond <stdint.h>.
 * Safe for -freestanding targets.
 */
#ifndef _ZSP_RTL_H
#define _ZSP_RTL_H

#include <stdint.h>

typedef uint64_t zsp_rtl_time_t;

/* Bit-slice helper: extract bits [hi:lo] from x */
#define ZSP_MASK(hi, lo)   (((uint64_t)1u << ((hi) - (lo) + 1u)) - 1u)
#define ZSP_SLICE(x, hi, lo) (((uint64_t)(x) >> (lo)) & ZSP_MASK(hi, lo))

/* Ceiling integer division (for wait_time lowering) */
#define ZSP_CEIL_DIV(n, d) (((n) + (d) - 1u) / (d))

#endif /* _ZSP_RTL_H */

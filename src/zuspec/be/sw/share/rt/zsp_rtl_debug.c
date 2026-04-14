/**
 * zsp_rtl_debug.c  —  runtime helpers for zuspec-be-rtl debug mode
 *
 * Compiled alongside generated C when -DZS_DEBUG is passed.
 */
#include "zsp_rtl_debug.h"
#include <stdio.h>

/* Per-thread head of the coroutine frame stack. */
_Thread_local ZspCoroFrame_t *zsp_coro_top = NULL;

/**
 * zsp_print_coro_stack  —  print the full coroutine stack to stderr.
 * Useful from GDB: `call zsp_print_coro_stack()`.
 */
void zsp_print_coro_stack(void)
{
    ZspCoroFrame_t *f = zsp_coro_top;
    if (!f) {
        fprintf(stderr, "<no active zuspec coroutines>\n");
        return;
    }
    int depth = 0;
    while (f) {
        fprintf(stderr, "#%-3d %s  [%s:%d]\n",
                depth,
                f->co_name  ? f->co_name  : "<unnamed>",
                f->loc.file ? f->loc.file : "<unknown>",
                f->loc.line);
        f = f->prev;
        depth++;
    }
}

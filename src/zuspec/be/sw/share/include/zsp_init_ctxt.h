
#ifndef INCLUDED_ZSP_INIT_CTXT_H
#define INCLUDED_ZSP_INIT_CTXT_H

struct zsp_alloc_s;
struct zsp_api_s;

typedef struct zsp_init_ctxt_s {
    struct zsp_alloc_s     *alloc;
    struct zsp_api_s       *api;
} zsp_init_ctxt_t;

#endif /* INCLUDED_ZSP_INIT_CTXT_H */
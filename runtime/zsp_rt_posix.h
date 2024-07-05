
#ifndef INCLUDED_ZSP_RT_POSIX_H
#define INCLUDED_ZSP_RT_POSIX_H
#include "zsp_rt.h"

typedef struct zsp_rt_addr_space_impl_s {

} zsp_rt_addr_space_impl_t;

typedef struct zsp_rt_addr_claim_impl_s {
    zsp_rt_addr_claim_t                 claim;
    struct zsp_rt_addr_claim_impl_s     *next;
} zsp_rt_addr_claim_impl_t;

typedef struct zsp_rt_actor_impl_s {
    zsp_rt_addr_claim_impl_t        *claim_free_l;
    
} zsp_rt_actor_impl_t;

#endif /* INCLUDED_ZSP_RT_POSIX_H */

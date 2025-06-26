
#ifndef INCLUDED_ZSP_CHANNEL_H
#define INCLUDED_ZSP_CHANNEL_H
#include "zsp/be/sw/rt/zsp_component.h"

struct zsp_frame_s;
struct zsp_thread_s;

typedef struct zsp_channel_s {
    zsp_component_t     base;
    int32_t             put_idx;
    int32_t             get_idx;
} zsp_channel_t;


void zsp_channel_init(
    const char          *name,
    zsp_component_t     *parent,
    int32_t             item_sz,
    int32_t             depth);

struct zsp_frame_s *zsp_channel_put(
    struct zsp_channel_s    *channel,
    uintptr_t               data);

struct zsp_frame_s *zsp_channel_put(
    struct zsp_channel_s    *channel,
    uintptr_t               data);


#endif /* INCLUDED_ZSP_CHANNEL_H */

#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void zsp_esw_notify(uint32_t pt);

void zsp_esw_wait(uint32_t executor_id, uint32_t pt);

#ifdef __cplusplus
}
#endif

#include "host_backend_sync.cpp"

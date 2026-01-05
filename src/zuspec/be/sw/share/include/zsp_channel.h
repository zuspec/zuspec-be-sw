/**
 * @file zsp_channel.h
 * @brief TLM-style FIFO channel for inter-component communication
 *
 * Provides a typed FIFO channel with blocking put/get operations and
 * non-blocking try_put/try_get variants. Works with the timebase scheduler
 * for coroutine-based blocking.
 */
#ifndef INCLUDED_ZSP_CHANNEL_H
#define INCLUDED_ZSP_CHANNEL_H

#include <stdint.h>
#include <stdbool.h>
#include "zsp_component.h"
#include "zsp_timebase.h"

#ifdef __cplusplus
extern "C" {
#endif

struct zsp_thread_s;
struct zsp_frame_s;

/*============================================================================
 * Channel Data Structure
 *============================================================================*/

/**
 * Generic FIFO channel structure.
 * 
 * The channel stores items as uintptr_t values (can hold pointers or small values).
 * For struct types, pointers to the struct should be stored.
 */
typedef struct zsp_channel_s {
    zsp_component_t     base;           /* Component base for naming/hierarchy */
    
    /* FIFO storage */
    uintptr_t           *buffer;        /* Circular buffer for items */
    uint32_t            capacity;       /* Maximum number of items */
    uint32_t            head;           /* Read index */
    uint32_t            tail;           /* Write index */
    uint32_t            count;          /* Current number of items */
    uint32_t            item_size;      /* Size of each item in bytes (0=uintptr) */
    
    /* Wait queues for blocking operations */
    struct zsp_thread_s *get_waiters;   /* Threads waiting for data */
    struct zsp_thread_s *put_waiters;   /* Threads waiting for space */
} zsp_channel_t;

/*============================================================================
 * PutIF and GetIF Interface Structures
 *============================================================================*/

/**
 * GetIF interface - consumer side of a channel.
 * Can be bound to a port to receive data.
 */
typedef struct zsp_get_if_s {
    void                *self;          /* Pointer to owning channel */
    /* Function pointers filled in at bind time */
} zsp_get_if_t;

/**
 * PutIF interface - producer side of a channel.
 * Can be bound to a port to send data.
 */
typedef struct zsp_put_if_s {
    void                *self;          /* Pointer to owning channel */
    /* Function pointers filled in at bind time */
} zsp_put_if_t;

/*============================================================================
 * Channel Initialization
 *============================================================================*/

/**
 * Initialize a channel with default capacity.
 *
 * @param ctxt      Initialization context (for allocator)
 * @param channel   Channel to initialize
 * @param name      Component name
 * @param parent    Parent component (may be NULL)
 * @param item_size Size of each item in bytes (0 for uintptr_t values)
 */
void zsp_channel_init(
    struct zsp_init_ctxt_s  *ctxt,
    zsp_channel_t           *channel,
    const char              *name,
    zsp_component_t         *parent,
    uint32_t                item_size);

/**
 * Initialize a channel with specified capacity.
 *
 * @param ctxt      Initialization context
 * @param channel   Channel to initialize
 * @param name      Component name
 * @param parent    Parent component
 * @param item_size Size of each item
 * @param capacity  Maximum number of items (0 = unlimited/default)
 */
void zsp_channel_init_capacity(
    struct zsp_init_ctxt_s  *ctxt,
    zsp_channel_t           *channel,
    const char              *name,
    zsp_component_t         *parent,
    uint32_t                item_size,
    uint32_t                capacity);

/*============================================================================
 * Non-Blocking Operations
 *============================================================================*/

/**
 * Try to put an item without blocking.
 *
 * @param channel   The channel
 * @param data      Data to put (or pointer to struct)
 * @return          true if successful, false if channel is full
 */
bool zsp_channel_try_put(zsp_channel_t *channel, uintptr_t data);

/**
 * Try to get an item without blocking.
 *
 * @param channel   The channel
 * @param out_data  Output pointer for retrieved data
 * @return          true if successful, false if channel is empty
 */
bool zsp_channel_try_get(zsp_channel_t *channel, uintptr_t *out_data);

/**
 * Check if channel has data available.
 */
bool zsp_channel_can_get(zsp_channel_t *channel);

/**
 * Check if channel has space for more data.
 */
bool zsp_channel_can_put(zsp_channel_t *channel);

/**
 * Get current number of items in channel.
 */
uint32_t zsp_channel_size(zsp_channel_t *channel);

/*============================================================================
 * Blocking Operations (Coroutine-style)
 *============================================================================*/

/**
 * Blocking put operation (coroutine task function).
 * 
 * Use with zsp_timebase scheduling. Blocks if channel is full.
 * The data value should be passed via va_args.
 */
struct zsp_frame_s *zsp_channel_put_task(
    struct zsp_timebase_s   *tb,
    struct zsp_thread_s     *thread,
    int                     idx,
    va_list                 *args);

/**
 * Blocking get operation (coroutine task function).
 *
 * Use with zsp_timebase scheduling. Blocks if channel is empty.
 * Returns data via thread->rval.
 */
struct zsp_frame_s *zsp_channel_get_task(
    struct zsp_timebase_s   *tb,
    struct zsp_thread_s     *thread,
    int                     idx,
    va_list                 *args);

/*============================================================================
 * Waiter Management (Internal)
 *============================================================================*/

/**
 * Add thread to get waiters list.
 */
void zsp_channel_add_get_waiter(zsp_channel_t *channel, struct zsp_thread_s *thread);

/**
 * Add thread to put waiters list.
 */
void zsp_channel_add_put_waiter(zsp_channel_t *channel, struct zsp_thread_s *thread);

/**
 * Wake up threads waiting for data (after put).
 */
void zsp_channel_notify_get_waiters(zsp_channel_t *channel);

/**
 * Wake up threads waiting for space (after get).
 */
void zsp_channel_notify_put_waiters(zsp_channel_t *channel);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDED_ZSP_CHANNEL_H */

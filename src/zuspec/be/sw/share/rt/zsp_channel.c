/**
 * @file zsp_channel.c
 * @brief TLM-style FIFO channel implementation
 */
#include <stdlib.h>
#include <string.h>
#include "zsp_channel.h"
#include "zsp_init_ctxt.h"
#include "zsp_timebase.h"

/* Default channel capacity when not specified */
#define ZSP_CHANNEL_DEFAULT_CAPACITY 16

/*============================================================================
 * Channel Initialization
 *============================================================================*/

void zsp_channel_init(
    zsp_init_ctxt_t     *ctxt,
    zsp_channel_t       *channel,
    const char          *name,
    zsp_component_t     *parent,
    uint32_t            item_size)
{
    zsp_channel_init_capacity(ctxt, channel, name, parent, item_size, 
                              ZSP_CHANNEL_DEFAULT_CAPACITY);
}

void zsp_channel_init_capacity(
    zsp_init_ctxt_t     *ctxt,
    zsp_channel_t       *channel,
    const char          *name,
    zsp_component_t     *parent,
    uint32_t            item_size,
    uint32_t            capacity)
{
    /* Initialize component base */
    zsp_component_init(ctxt, &channel->base, name, parent);
    
    /* Set up capacity (use default if 0) */
    channel->capacity = (capacity > 0) ? capacity : ZSP_CHANNEL_DEFAULT_CAPACITY;
    channel->item_size = item_size;
    
    /* Allocate buffer */
    channel->buffer = (uintptr_t *)ctxt->alloc->alloc(
        ctxt->alloc,
        channel->capacity * sizeof(uintptr_t));
    
    /* Initialize FIFO state */
    channel->head = 0;
    channel->tail = 0;
    channel->count = 0;
    
    /* Initialize wait queues */
    channel->get_waiters = NULL;
    channel->put_waiters = NULL;
}

/*============================================================================
 * Non-Blocking Operations
 *============================================================================*/

bool zsp_channel_try_put(zsp_channel_t *channel, uintptr_t data)
{
    if (channel->count >= channel->capacity) {
        return false;  /* Channel is full */
    }
    
    /* Add item to buffer */
    channel->buffer[channel->tail] = data;
    channel->tail = (channel->tail + 1) % channel->capacity;
    channel->count++;
    
    /* Wake up any get waiters */
    zsp_channel_notify_get_waiters(channel);
    
    return true;
}

bool zsp_channel_try_get(zsp_channel_t *channel, uintptr_t *out_data)
{
    if (channel->count == 0) {
        return false;  /* Channel is empty */
    }
    
    /* Remove item from buffer */
    *out_data = channel->buffer[channel->head];
    channel->head = (channel->head + 1) % channel->capacity;
    channel->count--;
    
    /* Wake up any put waiters */
    zsp_channel_notify_put_waiters(channel);
    
    return true;
}

bool zsp_channel_can_get(zsp_channel_t *channel)
{
    return channel->count > 0;
}

bool zsp_channel_can_put(zsp_channel_t *channel)
{
    return channel->count < channel->capacity;
}

uint32_t zsp_channel_size(zsp_channel_t *channel)
{
    return channel->count;
}

/*============================================================================
 * Waiter Management
 *============================================================================*/

void zsp_channel_add_get_waiter(zsp_channel_t *channel, zsp_thread_t *thread)
{
    // printf("DEBUG: Add get waiter %p\n", (void*)thread);
    /* Add to end of get waiters list */
    thread->next = NULL;
    if (channel->get_waiters == NULL) {
        channel->get_waiters = thread;
    } else {
        zsp_thread_t *tail = channel->get_waiters;
        while (tail->next != NULL) {
            tail = tail->next;
        }
        tail->next = thread;
    }
    /* Mark thread as blocked */
    thread->flags |= ZSP_THREAD_FLAGS_BLOCKED;
}

void zsp_channel_add_put_waiter(zsp_channel_t *channel, zsp_thread_t *thread)
{
    /* Add to end of put waiters list */
    thread->next = NULL;
    if (channel->put_waiters == NULL) {
        channel->put_waiters = thread;
    } else {
        zsp_thread_t *tail = channel->put_waiters;
        while (tail->next != NULL) {
            tail = tail->next;
        }
        tail->next = thread;
    }
    /* Mark thread as blocked */
    thread->flags |= ZSP_THREAD_FLAGS_BLOCKED;
}

void zsp_channel_notify_get_waiters(zsp_channel_t *channel)
{
    // printf("DEBUG: Notify get waiters (count=%d)\n", channel->count);
    /* Wake up one get waiter if data is available */
    while (channel->get_waiters != NULL && channel->count > 0) {
        zsp_thread_t *waiter = channel->get_waiters;
        channel->get_waiters = waiter->next;
        waiter->next = NULL;
        
        /* Clear blocked flag and schedule */
        waiter->flags &= ~ZSP_THREAD_FLAGS_BLOCKED;
        zsp_timebase_schedule(waiter->timebase, waiter);
    }
}

void zsp_channel_notify_put_waiters(zsp_channel_t *channel)
{
    /* Wake up one put waiter if space is available */
    while (channel->put_waiters != NULL && channel->count < channel->capacity) {
        zsp_thread_t *waiter = channel->put_waiters;
        channel->put_waiters = waiter->next;
        waiter->next = NULL;
        
        /* Clear blocked flag and schedule */
        waiter->flags &= ~ZSP_THREAD_FLAGS_BLOCKED;
        zsp_timebase_schedule(waiter->timebase, waiter);
    }
}

/*============================================================================
 * Blocking Operations (Coroutine Tasks)
 *============================================================================*/

/**
 * Blocking put task.
 * 
 * Locals:
 *   - channel: zsp_channel_t* (passed via args)
 *   - data: uintptr_t (passed via args)
 * 
 * States:
 *   0: Initial - try put, if fails block
 *   1: Resumed after block - retry put
 */
zsp_frame_t *zsp_channel_put_task(
    zsp_timebase_t  *tb,
    zsp_thread_t    *thread,
    int             idx,
    va_list         *args)
{
    zsp_frame_t *ret = thread->leaf;
    (void)tb;  /* Not used in channel operations */
    
    typedef struct {
        zsp_channel_t   *channel;
        uintptr_t       data;
    } locals_t;
    
    switch (idx) {
        case 0: {
            /* Allocate frame and extract args */
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &zsp_channel_put_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            
            if (args) {
                locals->channel = (zsp_channel_t *)va_arg(*args, void *);
                locals->data = va_arg(*args, uintptr_t);
            }
            
            /* Try to put */
            if (zsp_channel_try_put(locals->channel, locals->data)) {
                /* Success - return immediately */
                ret = zsp_timebase_return(thread, 0);
            } else {
                /* Channel full - block */
                ret->idx = 1;
                zsp_channel_add_put_waiter(locals->channel, thread);
            }
            break;
        }
        case 1: {
            /* Resumed after blocking - retry put */
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            
            if (zsp_channel_try_put(locals->channel, locals->data)) {
                ret = zsp_timebase_return(thread, 0);
            } else {
                /* Still full - block again */
                zsp_channel_add_put_waiter(locals->channel, thread);
            }
            break;
        }
    }
    
    return ret;
}

/**
 * Blocking get task.
 * 
 * Locals:
 *   - channel: zsp_channel_t* (passed via args)
 * 
 * Returns data via thread->rval
 */
zsp_frame_t *zsp_channel_get_task(
    zsp_timebase_t  *tb,
    zsp_thread_t    *thread,
    int             idx,
    va_list         *args)
{
    zsp_frame_t *ret = thread->leaf;
    (void)tb;  /* Not used in channel operations */
    
    typedef struct {
        zsp_channel_t   *channel;
    } locals_t;
    
    switch (idx) {
        case 0: {
            /* Allocate frame and extract args */
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &zsp_channel_get_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            
            if (args) {
                locals->channel = (zsp_channel_t *)va_arg(*args, void *);
            }
            
            /* Try to get */
            uintptr_t data;
            if (zsp_channel_try_get(locals->channel, &data)) {
                /* Success - return with data */
                ret = zsp_timebase_return(thread, data);
            } else {
                /* Channel empty - block */
                ret->idx = 1;
                zsp_channel_add_get_waiter(locals->channel, thread);
            }
            break;
        }
        case 1: {
            /* Resumed after blocking - retry get */
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            
            uintptr_t data;
            if (zsp_channel_try_get(locals->channel, &data)) {
                ret = zsp_timebase_return(thread, data);
            } else {
                /* Still empty - block again */
                zsp_channel_add_get_waiter(locals->channel, thread);
            }
            break;
        }
    }
    
    return ret;
}

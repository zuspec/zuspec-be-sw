/**
 * @file zsp_memory.h
 * @brief Memory storage implementation with flat and page-tree models
 * 
 * Provides memory storage that can be modeled as either:
 * - Flat array: for small memories (< threshold, default 64KB)
 * - Page tree: for large memories (>= threshold) using sparse allocation
 */

#ifndef INCLUDED_ZSP_MEMORY_H
#define INCLUDED_ZSP_MEMORY_H

#include <stdint.h>
#include <stdbool.h>
#include "zsp_component.h"
#include "zsp_init_ctxt.h"

/* Default threshold for switching from flat to page tree (64KB) */
#define ZSP_MEMORY_FLAT_THRESHOLD (64 * 1024)

/* Page size for page tree implementation (4KB) */
#define ZSP_MEMORY_PAGE_SIZE 4096

/* Forward declarations */
typedef struct zsp_memory_page zsp_memory_page_t;

/**
 * @brief Memory storage structure
 * 
 * Supports two storage models:
 * - Flat: single allocated array (for smaller memories)
 * - Paged: sparse page tree (for larger memories)
 */
typedef struct zsp_memory {
    zsp_component_t base;       /* Base component */
    uint32_t        size;       /* Total memory size in elements */
    uint8_t         width;      /* Element width in bits */
    bool            is_flat;    /* True if using flat array model */
    
    union {
        /* Flat array model */
        struct {
            void    *data;      /* Flat array data */
        } flat;
        
        /* Page tree model */
        struct {
            zsp_memory_page_t **pages;  /* Page table */
            uint32_t          page_count; /* Number of pages allocated */
        } paged;
    } storage;
} zsp_memory_t;

/**
 * @brief Initialize a memory with default flat threshold (64KB)
 * 
 * @param ctxt      Initialization context
 * @param mem       Memory instance to initialize
 * @param name      Component name
 * @param parent    Parent component
 * @param size      Memory size in elements
 * @param width     Element width in bits (8, 16, 32, or 64)
 */
void zsp_memory_init(
    zsp_init_ctxt_t *ctxt,
    zsp_memory_t    *mem,
    const char      *name,
    zsp_component_t *parent,
    uint32_t        size,
    uint8_t         width);

/**
 * @brief Initialize a memory with custom flat threshold
 * 
 * @param ctxt          Initialization context
 * @param mem           Memory instance to initialize
 * @param name          Component name
 * @param parent        Parent component
 * @param size          Memory size in elements
 * @param width         Element width in bits
 * @param flat_threshold Size threshold in bytes for flat vs paged model
 */
void zsp_memory_init_threshold(
    zsp_init_ctxt_t *ctxt,
    zsp_memory_t    *mem,
    const char      *name,
    zsp_component_t *parent,
    uint32_t        size,
    uint8_t         width,
    uint32_t        flat_threshold);

/**
 * @brief Read a value from memory
 * 
 * @param mem   Memory instance
 * @param addr  Element address (index)
 * @return      Value at address (0 if never written)
 */
uint64_t zsp_memory_read(zsp_memory_t *mem, uint32_t addr);

/**
 * @brief Write a value to memory
 * 
 * @param mem   Memory instance
 * @param addr  Element address (index)
 * @param data  Value to write
 */
void zsp_memory_write(zsp_memory_t *mem, uint32_t addr, uint64_t data);

/**
 * @brief Cleanup memory storage
 * 
 * @param mem   Memory instance to cleanup
 */
void zsp_memory_cleanup(zsp_memory_t *mem);

#endif /* INCLUDED_ZSP_MEMORY_H */

/**
 * @file zsp_memory.c
 * @brief Memory storage implementation
 */

#include "zsp_memory.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* Page structure for page tree implementation */
struct zsp_memory_page {
    void *data;  /* Page data */
};

/* Helper to calculate element size in bytes */
static inline uint32_t element_size_bytes(uint8_t width) {
    if (width <= 8) return 1;
    if (width <= 16) return 2;
    if (width <= 32) return 4;
    return 8;
}

/* Helper to calculate element mask for value truncation */
static inline uint64_t element_mask(uint8_t width) {
    if (width >= 64) return UINT64_MAX;
    return (1ULL << width) - 1;
}

void zsp_memory_init(
    zsp_init_ctxt_t *ctxt,
    zsp_memory_t    *mem,
    const char      *name,
    zsp_component_t *parent,
    uint32_t        size,
    uint8_t         width)
{
    zsp_memory_init_threshold(ctxt, mem, name, parent, size, width, 
                             ZSP_MEMORY_FLAT_THRESHOLD);
}

void zsp_memory_init_threshold(
    zsp_init_ctxt_t *ctxt,
    zsp_memory_t    *mem,
    const char      *name,
    zsp_component_t *parent,
    uint32_t        size,
    uint8_t         width,
    uint32_t        flat_threshold)
{
    /* Initialize base component */
    zsp_component_init(ctxt, &mem->base, name, parent);
    
    /* Store memory parameters */
    mem->size = size;
    mem->width = width;
    
    /* Calculate memory size in bytes */
    uint32_t elem_size = element_size_bytes(width);
    uint32_t total_bytes = size * elem_size;
    
    /* Choose storage model based on size */
    mem->is_flat = (total_bytes < flat_threshold);
    
    if (mem->is_flat) {
        /* Allocate flat array */
        mem->storage.flat.data = ctxt->alloc->alloc(ctxt->alloc, total_bytes);
        /* Zero-initialize for consistent read behavior */
        memset(mem->storage.flat.data, 0, total_bytes);
    } else {
        /* Initialize page tree */
        uint32_t elements_per_page = ZSP_MEMORY_PAGE_SIZE / elem_size;
        uint32_t num_pages = (size + elements_per_page - 1) / elements_per_page;
        
        mem->storage.paged.page_count = num_pages;
        mem->storage.paged.pages = (zsp_memory_page_t **)ctxt->alloc->alloc(
            ctxt->alloc, 
            num_pages * sizeof(zsp_memory_page_t *));
        
        /* Initialize page table to NULL (sparse allocation) */
        memset(mem->storage.paged.pages, 0, num_pages * sizeof(zsp_memory_page_t *));
    }
}

uint64_t zsp_memory_read(zsp_memory_t *mem, uint32_t addr)
{
    /* Bounds check */
    if (addr >= mem->size) {
        fprintf(stderr, "ERROR: Memory read out of bounds: addr=%u, size=%u\n", 
                addr, mem->size);
        return 0;
    }
    
    uint32_t elem_size = element_size_bytes(mem->width);
    
    if (mem->is_flat) {
        /* Flat array access */
        uint8_t *data = (uint8_t *)mem->storage.flat.data;
        uint8_t *elem_ptr = data + (addr * elem_size);
        
        /* Read value based on width */
        uint64_t value = 0;
        switch (elem_size) {
            case 1: value = *(uint8_t *)elem_ptr; break;
            case 2: value = *(uint16_t *)elem_ptr; break;
            case 4: value = *(uint32_t *)elem_ptr; break;
            case 8: value = *(uint64_t *)elem_ptr; break;
        }
        return value;
    } else {
        /* Page tree access */
        uint32_t elements_per_page = ZSP_MEMORY_PAGE_SIZE / elem_size;
        uint32_t page_idx = addr / elements_per_page;
        uint32_t page_offset = addr % elements_per_page;
        
        /* Check if page is allocated */
        zsp_memory_page_t *page = mem->storage.paged.pages[page_idx];
        if (page == NULL) {
            /* Page not allocated - return 0 */
            return 0;
        }
        
        /* Read from page */
        uint8_t *page_data = (uint8_t *)page->data;
        uint8_t *elem_ptr = page_data + (page_offset * elem_size);
        
        uint64_t value = 0;
        switch (elem_size) {
            case 1: value = *(uint8_t *)elem_ptr; break;
            case 2: value = *(uint16_t *)elem_ptr; break;
            case 4: value = *(uint32_t *)elem_ptr; break;
            case 8: value = *(uint64_t *)elem_ptr; break;
        }
        return value;
    }
}

void zsp_memory_write(zsp_memory_t *mem, uint32_t addr, uint64_t data)
{
    /* Bounds check */
    if (addr >= mem->size) {
        fprintf(stderr, "ERROR: Memory write out of bounds: addr=%u, size=%u\n", 
                addr, mem->size);
        return;
    }
    
    /* Mask data to element width */
    data = data & element_mask(mem->width);
    
    uint32_t elem_size = element_size_bytes(mem->width);
    
    if (mem->is_flat) {
        /* Flat array access */
        uint8_t *array_data = (uint8_t *)mem->storage.flat.data;
        uint8_t *elem_ptr = array_data + (addr * elem_size);
        
        /* Write value based on width */
        switch (elem_size) {
            case 1: *(uint8_t *)elem_ptr = (uint8_t)data; break;
            case 2: *(uint16_t *)elem_ptr = (uint16_t)data; break;
            case 4: *(uint32_t *)elem_ptr = (uint32_t)data; break;
            case 8: *(uint64_t *)elem_ptr = (uint64_t)data; break;
        }
    } else {
        /* Page tree access */
        uint32_t elements_per_page = ZSP_MEMORY_PAGE_SIZE / elem_size;
        uint32_t page_idx = addr / elements_per_page;
        uint32_t page_offset = addr % elements_per_page;
        
        /* Check if page is allocated */
        zsp_memory_page_t *page = mem->storage.paged.pages[page_idx];
        if (page == NULL) {
            /* Allocate page on first write */
            page = (zsp_memory_page_t *)malloc(sizeof(zsp_memory_page_t));
            page->data = malloc(ZSP_MEMORY_PAGE_SIZE);
            /* Zero-initialize page for consistent read behavior */
            memset(page->data, 0, ZSP_MEMORY_PAGE_SIZE);
            mem->storage.paged.pages[page_idx] = page;
        }
        
        /* Write to page */
        uint8_t *page_data = (uint8_t *)page->data;
        uint8_t *elem_ptr = page_data + (page_offset * elem_size);
        
        switch (elem_size) {
            case 1: *(uint8_t *)elem_ptr = (uint8_t)data; break;
            case 2: *(uint16_t *)elem_ptr = (uint16_t)data; break;
            case 4: *(uint32_t *)elem_ptr = (uint32_t)data; break;
            case 8: *(uint64_t *)elem_ptr = (uint64_t)data; break;
        }
    }
}

void zsp_memory_cleanup(zsp_memory_t *mem)
{
    if (mem->is_flat) {
        /* Free flat array */
        if (mem->storage.flat.data != NULL) {
            free(mem->storage.flat.data);
            mem->storage.flat.data = NULL;
        }
    } else {
        /* Free page tree */
        if (mem->storage.paged.pages != NULL) {
            for (uint32_t i = 0; i < mem->storage.paged.page_count; i++) {
                if (mem->storage.paged.pages[i] != NULL) {
                    if (mem->storage.paged.pages[i]->data != NULL) {
                        free(mem->storage.paged.pages[i]->data);
                    }
                    free(mem->storage.paged.pages[i]);
                }
            }
            free(mem->storage.paged.pages);
            mem->storage.paged.pages = NULL;
        }
    }
}

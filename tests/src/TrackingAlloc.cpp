/*
 * TrackingAlloc.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "TrackingAlloc.h"


namespace zsp {
namespace be {
namespace sw {

typedef struct block_s {
    int32_t         id;
    int32_t         busy;
} block_t;

static void *TrackingAlloc_alloc(TrackingAlloc *alloc, size_t sz) {
    block_t *block = (block_t *)malloc(sizeof(block_t) + sz);
    block->id = alloc->alloc_blocks.size();
    block->busy = 1;
    alloc->alloc_blocks.push_back(block);
    void *ret = (void *)((uintptr_t)block + sizeof(block_t));

    return ret;
}

static void TrackingAlloc_free(TrackingAlloc *alloc, void *ptr) {
    block_t *block = (block_t *)((uintptr_t)ptr - sizeof(block_t));
    int32_t id = -1;
    if (!block->busy) {
        fprintf(stdout, "Error: Attempt to free a block that is not busy\n");
    }

    for (std::vector<block_t *>::const_iterator it = alloc->alloc_blocks.begin();
         it != alloc->alloc_blocks.end(); ++it) {
        if (*it == block) {
            id = it - alloc->alloc_blocks.begin();
            break;
        }
    }

    if (id != -1) {
        alloc->free_blocks.push_back(block);
        alloc->alloc_blocks.erase(alloc->alloc_blocks.begin() + id);
    } else {
        fprintf(stdout, "Error: Block not found in allocation list\n");
    }
    
    // No free function for now
}

void TrackingAlloc_init(TrackingAlloc *alloc) {
    alloc->alloc.alloc = (zsp_alloc_func)&TrackingAlloc_alloc;
    alloc->alloc.free = (zsp_free_func)&TrackingAlloc_free; // No free function for now

    // Initialize other members if needed
}

void TrackingAlloc_dtor(TrackingAlloc *alloc) {
    for (std::vector<block_t *>::const_iterator it = alloc->alloc_blocks.begin();
         it != alloc->alloc_blocks.end(); ++it) {
        free(*it);
    }
    for (std::vector<block_t *>::const_iterator it = alloc->free_blocks.begin();
         it != alloc->free_blocks.end(); ++it) {
        free(*it);
    }
}

}
}
}

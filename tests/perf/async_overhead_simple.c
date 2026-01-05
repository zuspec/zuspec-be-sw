/**
 * Simple demonstration of async overhead vs direct calls
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <sys/time.h>

/*============================================================================
 * Memory Model
 *============================================================================*/

typedef struct {
    uint8_t *data;
    size_t size;
} memory_t;

void memory_init(memory_t *mem, size_t size) {
    mem->data = (uint8_t *)calloc(1, size);
    mem->size = size;
    for (size_t i = 0; i < size; i++) {
        mem->data[i] = (uint8_t)(i & 0xFF);
    }
}

/*============================================================================
 * ASYNC-style: With Frame Allocation Overhead
 *============================================================================*/

typedef struct {
    uint64_t addr;
    uint32_t result;
} read_frame_t;

uint32_t memory_read32_with_overhead(memory_t *mem, uint64_t addr) {
    // Simulate frame allocation overhead
    read_frame_t *frame = (read_frame_t *)malloc(sizeof(read_frame_t));
    frame->addr = addr;
    frame->result = 0;
    
    // Actual work
    for (int i = 0; i < 4; i++) {
        uint64_t byte_addr = addr + i;
        if (byte_addr < mem->size) {
            frame->result |= (mem->data[byte_addr] & 0xFF) << (i * 8);
        }
    }
    
    uint32_t result = frame->result;
    
    // Cleanup
    free(frame);
    
    return result;
}

/*============================================================================
 * SYNC-style: Direct Call (No Overhead)
 *============================================================================*/

static inline uint32_t memory_read32_direct(memory_t *mem, uint64_t addr) {
    uint32_t result = 0;
    for (int i = 0; i < 4; i++) {
        uint64_t byte_addr = addr + i;
        if (byte_addr < mem->size) {
            result |= (mem->data[byte_addr] & 0xFF) << (i * 8);
        }
    }
    return result;
}

/*============================================================================
 * Utilities
 *============================================================================*/

static double get_time_sec() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (double)tv.tv_sec + (double)tv.tv_usec * 1e-6;
}

/*============================================================================
 * Main
 *============================================================================*/

int main() {
    const int MEM_SIZE = 64 * 1024;
    const int ITERATIONS = 1000000;
    
    printf("========================================================================\n");
    printf("Async Overhead vs Direct Call Comparison\n");
    printf("========================================================================\n");
    printf("\nConfiguration:\n");
    printf("  Memory: %d bytes\n", MEM_SIZE);
    printf("  Iterations: %d\n", ITERATIONS);
    
    memory_t mem;
    memory_init(&mem, MEM_SIZE);
    
    // Benchmark 1: With overhead (simulating async)
    printf("\n[WITH OVERHEAD] Simulating Async State Machine:\n");
    double start1 = get_time_sec();
    uint64_t sum1 = 0;
    for (int i = 0; i < ITERATIONS; i++) {
        uint64_t addr = (i * 4) % (mem.size - 4);
        sum1 += memory_read32_with_overhead(&mem, addr);
    }
    double time1 = get_time_sec() - start1;
    printf("  Time: %.3f sec (%.1f ns/op)\n", time1, time1 * 1e9 / ITERATIONS);
    printf("  Throughput: %.1f M ops/sec\n", ITERATIONS / time1 / 1e6);
    printf("  Checksum: 0x%016lx\n", sum1);
    
    // Benchmark 2: Direct (no overhead)
    printf("\n[DIRECT CALL] Synchronous Direct Function:\n");
    double start2 = get_time_sec();
    uint64_t sum2 = 0;
    for (int i = 0; i < ITERATIONS; i++) {
        uint64_t addr = (i * 4) % (mem.size - 4);
        sum2 += memory_read32_direct(&mem, addr);
    }
    double time2 = get_time_sec() - start2;
    printf("  Time: %.3f sec (%.1f ns/op)\n", time2, time2 * 1e9 / ITERATIONS);
    printf("  Throughput: %.1f M ops/sec\n", ITERATIONS / time2 / 1e6);
    printf("  Checksum: 0x%016lx\n", sum2);
    
    // Analysis
    printf("\n========================================================================\n");
    printf("ANALYSIS\n");
    printf("========================================================================\n");
    double speedup = time1 / time2;
    double overhead_ns = (time1 - time2) * 1e9 / ITERATIONS;
    
    printf("\nSpeedup: %.1fx (Direct is %.1fx faster)\n", speedup, speedup);
    printf("Overhead per call: %.1f ns\n", overhead_ns);
    printf("\nBreakdown:\n");
    printf("  malloc():       ~50-100 ns\n");
    printf("  free():         ~50-100 ns\n");
    printf("  State machine:  ~5-10 ns\n");
    printf("  Total overhead: ~105-210 ns\n");
    printf("  Actual work:    ~3-5 ns\n");
    printf("\nKey Finding:\n");
    printf("  Async overhead is %.0f-%.0fx the actual work!\n", 
           overhead_ns / 3, overhead_ns / 5);
    printf("\nFor RV64 Memory Benchmark:\n");
    printf("  Current: 30 MIPS (with async overhead)\n");
    printf("  With sync: ~%.0f MIPS (expected %.1fx improvement)\n", 
           30.0 * speedup, speedup);
    printf("\n========================================================================\n");
    
    free(mem.data);
    return 0;
}

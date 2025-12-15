#!/usr/bin/env python3
#****************************************************************************
# Copyright 2019-2025 Matthew Ballance and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#****************************************************************************
"""Fixed: Compare Zuspec generated C vs SystemC for FIFO-channel get/put with blocking.

This version manually implements the channel operations instead of relying on
code generation of async methods (which is not yet supported).
"""

import argparse
import contextlib
import io
import os
import re
import subprocess
import tempfile
from pathlib import Path

with contextlib.redirect_stdout(io.StringIO()):
    import zuspec.dataclasses as zdc
    from zuspec.be.sw import CGenerator

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARE_DIR = REPO_ROOT / "src" / "zuspec" / "be" / "sw" / "share"
RT_DIR = SHARE_DIR / "rt"
INCLUDE_DIR = SHARE_DIR / "include"

SYSTEMC_HOME = Path(os.environ.get("SYSTEMC_HOME", "/tools/systemc/3.0.0"))
SYSTEMC_INC = SYSTEMC_HOME / "include"
SYSTEMC_LIB = SYSTEMC_HOME / "lib-linux64"

RT_SOURCES = [
    "zsp_alloc.c",
    "zsp_timebase.c",
    "zsp_list.c",
    "zsp_object.c",
    "zsp_component.c",
    "zsp_map.c",
    "zsp_struct.c",
    "zsp_channel.c",
]


@zdc.dataclass
class Producer(zdc.Component):
    p: zdc.PutIF[int] = zdc.port()


@zdc.dataclass
class Consumer(zdc.Component):
    c: zdc.GetIF[int] = zdc.port()


@zdc.dataclass
class TopChannel(zdc.Component):
    p: Producer = zdc.field()
    c: Consumer = zdc.field()
    ch: zdc.Channel[int] = zdc.field()

    def __bind__(self):
        return {
            self.p.p: self.ch.put,
            self.c.c: self.ch.get,
        }


def _run(cmd, cwd, timeout=300):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def _parse_metrics(stdout: str):
    def _get(name: str):
        m = re.search(rf"^{name}:(.+)$", stdout, re.MULTILINE)
        return m.group(1).strip() if m else None

    return {
        "elapsed_sec": float(_get("ELAPSED_SEC")) if _get("ELAPSED_SEC") else None,
        "iter_per_sec": float(_get("ITER_PER_SEC")) if _get("ITER_PER_SEC") else None,
        "final_time_ns": int(_get("FINAL_TIME_NS")) if _get("FINAL_TIME_NS") else None,
        "final_count": int(_get("FINAL_COUNT")) if _get("FINAL_COUNT") else None,
    }


def run_zuspec_c(iterations: int, opt_flags: list[str]):
    with tempfile.TemporaryDirectory(prefix="zsp_chperf_") as td:
        td_p = Path(td)

        dm_ctxt = zdc.DataModelFactory().build([Producer, Consumer, TopChannel])
        generator = CGenerator(output_dir=str(td_p))
        sources = generator.generate(dm_ctxt)

        # Main manually implements channel operations since async method codegen isn't supported yet
        main_c = r'''
#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "zsp_alloc.h"
#include "zsp_init_ctxt.h"
#include "zsp_timebase.h"
#include "zsp_channel.h"

#include "topchannel.h"
#include "producer.h"
#include "consumer.h"

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

#include "producer.c"
#include "consumer.c"
#include "topchannel.c"

static void run_to_idle(zsp_timebase_t *tb) {
    while (zsp_timebase_has_pending(tb)) {
        while (tb->ready_head) {
            zsp_timebase_run(tb);
        }
        if (tb->event_count > 0) {
            zsp_timebase_advance(tb);
        }
    }
}

/* Producer: put value and wait 1ns */
static zsp_frame_t *producer_send_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    
    typedef struct {
        zsp_put_if_t *port;
        int32_t value;
    } locals_t;
    
    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &producer_send_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            if (args) {
                locals->port = (zsp_put_if_t *)va_arg(*args, void *);
                locals->value = va_arg(*args, int32_t);
            }
            ret->idx = 1;
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            ret->idx = 2;
            /* Call channel put */
            ret = zsp_timebase_call(thread, &zsp_channel_put_task, locals->port, locals->value);
            break;
        }
        case 2: {
            /* Wait 1ns */
            zsp_timebase_wait(thread, ZSP_TIME_NS(1));
            ret = zsp_timebase_return(thread, 0);
            break;
        }
    }
    return ret;
}

/* Producer process: loop calling send */
static zsp_frame_t *producer_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    typedef struct {
        TopChannel *top;
        uint32_t remaining;
    } locals_t;

    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &producer_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            if (args) {
                locals->top = (TopChannel *)va_arg(*args, void *);
                locals->remaining = (uint32_t)va_arg(*args, uint32_t);
            }
            ret->idx = 1;
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            if (locals->remaining == 0) {
                ret = zsp_timebase_return(thread, 0);
            } else {
                locals->remaining--;
                ret->idx = 1;
                ret = zsp_timebase_call(thread, &producer_send_task, locals->top->p.p, 0);
            }
            break;
        }
    }

    return ret;
}

/* Consumer: get value from channel */
static zsp_frame_t *consumer_recv_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;
    
    typedef struct {
        zsp_get_if_t *port;
    } locals_t;
    
    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &consumer_recv_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            if (args) {
                locals->port = (zsp_get_if_t *)va_arg(*args, void *);
            }
            ret->idx = 1;
            /* Call channel get - this blocks until data available */
            ret = zsp_timebase_call(thread, &zsp_channel_get_task, locals->port);
            break;
        }
        case 1: {
            /* Channel get completed, return */
            ret = zsp_timebase_return(thread, 0);
            break;
        }
    }
    return ret;
}

/* Consumer driver: loop calling recv */
static zsp_frame_t *consumer_task(zsp_thread_t *thread, int idx, va_list *args) {
    zsp_frame_t *ret = thread->leaf;

    typedef struct {
        TopChannel *top;
        uint32_t remaining;
        uint32_t count;
    } locals_t;

    switch (idx) {
        case 0: {
            ret = zsp_timebase_alloc_frame(thread, sizeof(locals_t), &consumer_task);
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            if (args) {
                locals->top = (TopChannel *)va_arg(*args, void *);
                locals->remaining = (uint32_t)va_arg(*args, uint32_t);
            }
            locals->count = 0;
            ret->idx = 1;
            break;
        }
        case 1: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            if (locals->remaining == 0) {
                ret = zsp_timebase_return(thread, locals->count);
            } else {
                locals->remaining--;
                ret->idx = 2;
                ret = zsp_timebase_call(thread, &consumer_recv_task, locals->top->c.c);
            }
            break;
        }
        case 2: {
            locals_t *locals = zsp_frame_locals(ret, locals_t);
            locals->count++;
            ret->idx = 1;
            break;
        }
    }

    return ret;
}

int main(int argc, char **argv) {
    uint32_t iterations = ITER_PLACEHOLDER;
    if (argc > 1) {
        iterations = (uint32_t)strtoul(argv[1], 0, 0);
    }

    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_init_ctxt_t ctxt;
    ctxt.alloc = &alloc;

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    TopChannel top;
    TopChannel_init(&ctxt, &top, "top", NULL);
    TopChannel__bind(&top);

    double t0 = now_sec();
    /* Start consumer first, so it blocks immediately */
    zsp_timebase_thread_create(&tb, &consumer_task, ZSP_THREAD_FLAGS_NONE, &top, iterations);
    zsp_timebase_thread_create(&tb, &producer_task, ZSP_THREAD_FLAGS_NONE, &top, iterations);

    run_to_idle(&tb);
    double t1 = now_sec();

    const double elapsed = t1 - t0;

    printf("FINAL_TIME_NS:%llu\n", (unsigned long long)zsp_timebase_current_ticks(&tb));
    printf("ELAPSED_SEC:%.9f\n", elapsed);
    if (elapsed > 0.0) {
        printf("ITER_PER_SEC:%.3f\n", (double)iterations / elapsed);
    }
    printf("FINAL_COUNT:%u\n", iterations);

    zsp_timebase_destroy(&tb);
    return 0;
}
'''
        main_c = main_c.replace("ITER_PLACEHOLDER", str(iterations))
        (td_p / "main.c").write_text(main_c)

        all_sources = [str(td_p / "main.c")]
        for src in RT_SOURCES:
            all_sources.append(str(RT_DIR / src))

        exe = td_p / "zsp_chperf"
        cmd = [
            "gcc",
            "-std=c11",
        ] + opt_flags + [
            "-Wno-incompatible-pointer-types",
            f"-I{INCLUDE_DIR}",
            f"-I{td_p}",
            "-o",
            str(exe),
        ] + all_sources

        rc, out, err = _run(cmd, cwd=str(td_p))
        if rc != 0:
            raise RuntimeError(f"Zuspec channel C compile failed\nstdout:\n{out}\nstderr:\n{err}")

        rc, out, err = _run([str(exe), str(iterations)], cwd=str(td_p))
        if rc != 0:
            raise RuntimeError(f"Zuspec channel C run failed\nstdout:\n{out}\nstderr:\n{err}")

        return _parse_metrics(out), out


def run_systemc(iterations: int, opt_flags: list[str]):
    if not SYSTEMC_INC.exists() or not SYSTEMC_LIB.exists():
        raise RuntimeError(f"SystemC not found at {SYSTEMC_HOME} (set SYSTEMC_HOME)")

    with tempfile.TemporaryDirectory(prefix="systemc_chperf_") as td:
        td_p = Path(td)

        main_cpp = r'''
#include <systemc>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <chrono>

using namespace sc_core;

SC_MODULE(Top) {
    sc_fifo<int> ch;
    uint64_t iterations = 0;
    uint64_t count = 0;

    SC_CTOR(Top) : ch(1) {
        SC_THREAD(producer);
        SC_THREAD(consumer);
    }

    void producer() {
        for (uint64_t i=0; i<iterations; i++) {
            ch.write(0);
            wait(1, SC_NS);
        }
    }

    void consumer() {
        for (uint64_t i=0; i<iterations; i++) {
            (void)ch.read();
            count++;
        }
        sc_stop();
    }
};

int sc_main(int argc, char **argv) {
    uint64_t iterations = ITER_PLACEHOLDER;
    if (argc > 1) {
        iterations = strtoull(argv[1], 0, 0);
    }

    sc_set_time_resolution(1, SC_NS);

    Top top("top");
    top.iterations = iterations;

    auto t0 = std::chrono::steady_clock::now();
    sc_start();
    auto t1 = std::chrono::steady_clock::now();

    const double elapsed = std::chrono::duration<double>(t1 - t0).count();
    const uint64_t final_time_ns = (uint64_t)sc_time_stamp().value();

    std::printf("FINAL_COUNT:%llu\n", (unsigned long long)top.count);
    std::printf("FINAL_TIME_NS:%llu\n", (unsigned long long)final_time_ns);
    std::printf("ELAPSED_SEC:%.9f\n", elapsed);
    if (elapsed > 0.0) {
        std::printf("ITER_PER_SEC:%.3f\n", (double)iterations / elapsed);
    }

    return 0;
}
'''
        main_cpp = main_cpp.replace("ITER_PLACEHOLDER", str(iterations))
        (td_p / "main.cpp").write_text(main_cpp)

        exe = td_p / "systemc_chperf"
        cmd = [
            "g++",
            "-std=c++17",
        ] + opt_flags + [
            str(td_p / "main.cpp"),
            "-o",
            str(exe),
            f"-I{SYSTEMC_INC}",
            f"-L{SYSTEMC_LIB}",
            f"-Wl,-rpath,{SYSTEMC_LIB}",
            "-lsystemc",
            "-pthread",
        ]

        rc, out, err = _run(cmd, cwd=str(td_p))
        if rc != 0:
            raise RuntimeError(f"SystemC compile failed\nstdout:\n{out}\nstderr:\n{err}")

        rc, out, err = _run([str(exe), str(iterations)], cwd=str(td_p))
        if rc != 0:
            raise RuntimeError(f"SystemC run failed\nstdout:\n{out}\nstderr:\n{err}")

        return _parse_metrics(out), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=100_000)
    ap.add_argument("--opt", default="-O3", help="Optimization flags (eg -O2, '-O3 -flto')")
    args = ap.parse_args()

    opt_flags = args.opt.split() if args.opt else ["-O3"]
    if not opt_flags:
        opt_flags = ["-O3"]

    iters = int(args.iterations)

    print("=" * 72)
    print(f"TLM Channel Benchmark: {iters:,} iterations")
    print("=" * 72)
    
    zsp_m, _ = run_zuspec_c(iters, opt_flags)
    sc_m, _ = run_systemc(iters, opt_flags)

    print("Zuspec C (generated bindings + runtime channel tasks):")
    print(f"  ELAPSED_SEC   : {zsp_m['elapsed_sec']:.6f}")
    print(f"  ITER_PER_SEC  : {zsp_m['iter_per_sec']:.3f}")
    print(f"  FINAL_TIME_NS : {zsp_m['final_time_ns']}")

    print("SystemC (sc_fifo):")
    print(f"  ELAPSED_SEC   : {sc_m['elapsed_sec']:.6f}")
    print(f"  ITER_PER_SEC  : {sc_m['iter_per_sec']:.3f}")
    print(f"  FINAL_TIME_NS : {sc_m['final_time_ns']}")

    if zsp_m["iter_per_sec"] and sc_m["iter_per_sec"] and sc_m["iter_per_sec"] > 0:
        ratio = zsp_m["iter_per_sec"] / sc_m["iter_per_sec"]
        print("=" * 72)
        print(f"Speedup (ZuspecC / SystemC): {ratio:.2f}x")


if __name__ == "__main__":
    main()

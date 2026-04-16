"""Inference C emission helpers.

Generates C code for buffer pipeline, stream joint-solve, and
schedule-block stage tables from SwNode inference IR.

Design ref: schedule-buffer-stream-inference-plan.md Sections 3.2.4, 4.2.3, 5.3.4
"""
from __future__ import annotations

import io
from typing import Dict, List, Optional

from zuspec.be.sw.ir.inference import (
    SwBufferSolveFunc,
    SwStreamJointSolveFunc,
    SwScheduleStageTable,
)


def emit_buffer_param_struct(node: SwBufferSolveFunc) -> str:
    """Emit the parameter struct for passing buffer values producer -> consumer."""
    out = io.StringIO()
    struct_name = f"{node.producer_type}_{node.consumer_type}_buf"
    out.write(f"/* Buffer parameter struct: {node.producer_type} -> {node.consumer_type} */\n")
    out.write(f"typedef struct {{\n")
    for fname in node.shared_fields:
        out.write(f"    uint32_t  {fname};\n")
    out.write(f"}} {struct_name}_t;\n\n")
    return out.getvalue()


def emit_buffer_producer_solve(node: SwBufferSolveFunc) -> str:
    """Emit the producer solve function with back-propagated constraints."""
    out = io.StringIO()
    func_name = f"solve_{node.producer_type}"
    struct_name = f"{node.producer_type}_{node.consumer_type}_buf"
    fields_type = f"{node.producer_type}_fields_t"

    out.write(f"/* Generated: producer solves with consumer's back-propagated constraints */\n")
    out.write(f"static SolveResult {func_name}(\n")
    out.write(f"    solve_buf_t *buf, uint64_t seed,\n")
    out.write(f"    {fields_type} *out) {{\n")
    out.write(f"    SolveProblem *sp = solve_problem_init(buf->data, buf->size);\n")

    # Emit variable declarations for shared fields
    for i, fname in enumerate(node.shared_fields):
        out.write(f"    problem_add_var(sp, {i}, 32, 0, 0, 0xFFFFFFFF);  /* {fname} */\n")

    # Emit back-propagated constraints as comments (actual constraint
    # emission depends on the specific constraint structure)
    for c in node.backprop_constraints:
        field = c.get("field_name", "?")
        op = c.get("op", "?")
        bound = c.get("bound", "?")
        out.write(f"    /* Back-propagated: {field} {op} {bound} */\n")

    out.write(f"    /* ... solve and extract values ... */\n")
    out.write(f"    return SOLVE_OK;\n")
    out.write(f"}}\n\n")
    return out.getvalue()


def emit_buffer_consumer_solve(node: SwBufferSolveFunc) -> str:
    """Emit the consumer solve function with fixed buffer values."""
    out = io.StringIO()
    func_name = f"solve_{node.consumer_type}"
    buf_struct = f"{node.producer_type}_{node.consumer_type}_buf"

    out.write(f"/* Generated: consumer receives concrete values from producer */\n")
    out.write(f"static SolveResult {func_name}(\n")
    out.write(f"    solve_buf_t *buf, uint64_t seed,\n")
    out.write(f"    const {buf_struct}_t *input_buf) {{\n")
    out.write(f"    SolveProblem *sp = solve_problem_init(buf->data, buf->size);\n")

    # Buffer fields fixed to producer's solved values (lo == hi)
    for i, fname in enumerate(node.shared_fields):
        out.write(f"    problem_add_var(sp, {i}, 32, 0,\n")
        out.write(f"                   input_buf->{fname}, input_buf->{fname});  /* {fname} */\n")

    out.write(f"    /* ... consumer's own rand fields + solve ... */\n")
    out.write(f"    return SOLVE_OK;\n")
    out.write(f"}}\n\n")
    return out.getvalue()


def emit_stream_joint_solve(node: SwStreamJointSolveFunc) -> str:
    """Emit the merged stream solve function."""
    out = io.StringIO()
    pair_name = f"{node.producer_type}_{node.consumer_type}_stream_pair"

    # Emit combined fields struct
    out.write(f"/* Stream pair fields: {node.producer_type} + {node.consumer_type} */\n")
    out.write(f"typedef struct {{\n")
    out.write(f"    /* Shared stream fields */\n")
    for fname in node.shared_fields:
        out.write(f"    uint32_t  {fname};\n")
    if node.producer_private_fields:
        out.write(f"    /* Producer-side fields */\n")
        for fname in node.producer_private_fields:
            out.write(f"    uint32_t  {fname};\n")
    if node.consumer_private_fields:
        out.write(f"    /* Consumer-side fields */\n")
        for fname in node.consumer_private_fields:
            out.write(f"    uint32_t  {fname};\n")
    out.write(f"}} {pair_name}_fields_t;\n\n")

    # Emit solve function
    out.write(f"/* Generated: stream producer + consumer solved jointly */\n")
    out.write(f"static SolveResult solve_{pair_name}(\n")
    out.write(f"    solve_buf_t *buf, uint64_t seed,\n")
    out.write(f"    {pair_name}_fields_t *out) {{\n")
    out.write(f"    SolveProblem *sp = solve_problem_init(buf->data, buf->size);\n")

    var_id = 0
    # Shared fields: one variable each
    for fname in node.shared_fields:
        out.write(f"    problem_add_var(sp, {var_id}, 32, 0, 0, 0xFFFFFFFF);  /* {fname} (shared) */\n")
        var_id += 1

    # Producer private fields
    for fname in node.producer_private_fields:
        out.write(f"    problem_add_var(sp, {var_id}, 32, 0, 0, 0xFFFFFFFF);  /* {fname} (producer) */\n")
        var_id += 1

    # Consumer private fields
    for fname in node.consumer_private_fields:
        out.write(f"    problem_add_var(sp, {var_id}, 32, 0, 0, 0xFFFFFFFF);  /* {fname} (consumer) */\n")
        var_id += 1

    out.write(f"    /* Both sides' constraints reference unified var_ids */\n")
    out.write(f"    /* ... constraints + solve ... */\n")
    out.write(f"    return SOLVE_OK;\n")
    out.write(f"}}\n\n")
    return out.getvalue()


def emit_schedule_stage_table(node: SwScheduleStageTable) -> str:
    """Emit static const stage tables for a schedule block."""
    out = io.StringIO()
    name = node.schedule_name
    name_upper = name.upper()

    out.write(f"/* Generated: schedule block \"{name}\" ")
    out.write(f"with {node.n_actions} actions, {node.n_stages} stages */\n")

    # Compute maximum units per stage and actions per stage
    max_units = max((len(stage) for stage in node.stages), default=0)
    max_actions = max(
        (sum(len(unit) for unit in stage) for stage in node.stages),
        default=0,
    )

    out.write(f"#define {name_upper}_MAX_UNITS_PER_STAGE  {max(max_units, 1)}u\n")
    out.write(f"#define {name_upper}_MAX_ACTIONS_PER_STAGE {max(max_actions, 1)}u\n")
    out.write(f"#define {name_upper}_N_STAGES {node.n_stages}\n\n")

    out.write(f"typedef struct {{\n")
    out.write(f"    uint8_t  n_units;\n")
    out.write(f"    uint8_t  unit_sizes[{name_upper}_MAX_UNITS_PER_STAGE];\n")
    out.write(f"    uint8_t  action_ids[{name_upper}_MAX_ACTIONS_PER_STAGE];\n")
    out.write(f"}} {name}_stage_t;\n\n")

    out.write(f"static const {name}_stage_t {name}_stages[] = {{\n")
    for level, stage in enumerate(node.stages):
        n_units = len(stage)
        unit_sizes = [len(unit) for unit in stage]
        action_ids = [aid for unit in stage for aid in unit]

        us_str = ", ".join(str(s) for s in unit_sizes)
        ai_str = ", ".join(str(a) for a in action_ids)

        out.write(f"    {{ .n_units = {n_units}, ")
        out.write(f".unit_sizes = {{{us_str}}}, ")
        out.write(f".action_ids = {{{ai_str}}} }},")
        out.write(f"  /* stage {level} */\n")

    out.write(f"}};\n\n")

    # Emit dispatch skeleton
    out.write(f"/* Runtime dispatch: iterate stages, spawn units, join */\n")
    out.write(f"static void {name}_dispatch(\n")
    out.write(f"    zsp_timebase_t *tb,\n")
    out.write(f"    zsp_task_fn_t *action_funcs[{node.n_actions}]) {{\n")
    out.write(f"    for (int s = 0; s < {name_upper}_N_STAGES; s++) {{\n")
    out.write(f"        const {name}_stage_t *stage = &{name}_stages[s];\n")
    out.write(f"        uint8_t off = 0;\n")
    out.write(f"        for (uint8_t u = 0; u < stage->n_units; u++) {{\n")
    out.write(f"            for (uint8_t a = 0; a < stage->unit_sizes[u]; a++) {{\n")
    out.write(f"                uint8_t act_id = stage->action_ids[off++];\n")
    out.write(f"                zsp_timebase_thread_create(tb, action_funcs[act_id],\n")
    out.write(f"                                           0, NULL);\n")
    out.write(f"            }}\n")
    out.write(f"        }}\n")
    out.write(f"        /* Join: wait for all threads in this stage */\n")
    out.write(f"        zsp_timebase_join_all(tb);\n")
    out.write(f"    }}\n")
    out.write(f"}}\n")
    return out.getvalue()

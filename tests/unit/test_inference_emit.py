"""Unit tests for inference C emission helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from zuspec.be.sw.ir.inference import (
    SwBufferSolveFunc,
    SwStreamJointSolveFunc,
    SwScheduleStageTable,
)
from zuspec.be.sw.passes.inference_emit import (
    emit_buffer_param_struct,
    emit_buffer_producer_solve,
    emit_buffer_consumer_solve,
    emit_stream_joint_solve,
    emit_schedule_stage_table,
)


class TestBufferEmit:

    def test_param_struct(self):
        node = SwBufferSolveFunc(
            producer_type="data_writer",
            consumer_type="data_reader",
            shared_fields=["addr", "data"],
        )
        code = emit_buffer_param_struct(node)
        assert "data_writer_data_reader_buf_t" in code
        assert "uint32_t  addr;" in code
        assert "uint32_t  data;" in code

    def test_producer_solve_function(self):
        node = SwBufferSolveFunc(
            producer_type="data_writer",
            consumer_type="data_reader",
            shared_fields=["addr", "data"],
            backprop_constraints=[
                {"field_name": "addr", "op": "gte", "bound": 0x100},
            ],
        )
        code = emit_buffer_producer_solve(node)
        assert "solve_data_writer" in code
        assert "Back-propagated: addr gte" in code
        assert "problem_add_var" in code

    def test_consumer_solve_function(self):
        node = SwBufferSolveFunc(
            producer_type="data_writer",
            consumer_type="data_reader",
            shared_fields=["addr", "data"],
        )
        code = emit_buffer_consumer_solve(node)
        assert "solve_data_reader" in code
        assert "input_buf->addr" in code
        assert "input_buf->data" in code


class TestStreamEmit:

    def test_joint_solve_function(self):
        node = SwStreamJointSolveFunc(
            producer_type="tx_action",
            consumer_type="rx_action",
            shared_fields=["payload", "tag"],
            producer_private_fields=["internal"],
            consumer_private_fields=["mode"],
        )
        code = emit_stream_joint_solve(node)
        assert "tx_action_rx_action_stream_pair_fields_t" in code
        assert "payload" in code and "(shared)" in code
        assert "internal" in code and "(producer)" in code
        assert "mode" in code and "(consumer)" in code
        assert "solve_tx_action_rx_action_stream_pair" in code


class TestScheduleEmit:

    def test_stage_table(self):
        """3 stages, 6 actions, mixed unit sizes."""
        node = SwScheduleStageTable(
            schedule_name="my_sched",
            n_stages=3,
            n_actions=6,
            stages=[
                [[0]],              # stage 0: 1 unit, 1 action
                [[1], [2, 3]],      # stage 1: 2 units (1 + 2 actions)
                [[4, 5]],           # stage 2: 1 unit, 2 actions
            ],
        )
        code = emit_schedule_stage_table(node)
        assert "MY_SCHED_N_STAGES 3" in code
        assert "my_sched_stage_t" in code
        assert "my_sched_stages[]" in code
        assert "my_sched_dispatch" in code
        assert "stage 0" in code
        assert "stage 1" in code
        assert "stage 2" in code
        # Verify the dispatch function structure
        assert "zsp_timebase_thread_create" in code
        assert "zsp_timebase_join_all" in code

    def test_single_stage(self):
        node = SwScheduleStageTable(
            schedule_name="simple",
            n_stages=1,
            n_actions=2,
            stages=[[[0, 1]]],
        )
        code = emit_schedule_stage_table(node)
        assert "SIMPLE_N_STAGES 1" in code
        assert ".n_units = 1" in code

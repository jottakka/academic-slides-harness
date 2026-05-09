import pytest
from transitions.core import MachineError

from academic_slides_harness.core.state_machines import PipelineMachine, ToolCallMachine


def test_pipeline_state_machine_accepts_expected_happy_path() -> None:
    pipeline = PipelineMachine()

    pipeline.ingest_started()
    pipeline.ingest_completed()
    pipeline.planning_started()
    pipeline.planning_completed()
    pipeline.render_started()
    pipeline.render_completed()
    pipeline.visualizing_started()
    pipeline.visualizing_completed()
    pipeline.validation_started()
    pipeline.validation_completed()

    assert pipeline.state == "validated"


def test_pipeline_state_machine_rejects_out_of_order_rendering() -> None:
    pipeline = PipelineMachine()

    with pytest.raises(MachineError):
        pipeline.render_started()


def test_tool_call_state_machine_tracks_elicitation_and_completion() -> None:
    tool_call = ToolCallMachine()

    tool_call.receive()
    tool_call.elicit()
    tool_call.resume()
    tool_call.report_progress()
    tool_call.complete()

    assert tool_call.state == "completed"


def test_tool_call_state_machine_tracks_recoverable_tool_errors() -> None:
    tool_call = ToolCallMachine()

    tool_call.receive()
    tool_call.start()
    tool_call.fail_tool()

    assert tool_call.state == "tool_error"

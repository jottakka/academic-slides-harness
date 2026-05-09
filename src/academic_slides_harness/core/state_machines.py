from __future__ import annotations

from typing import ClassVar

from transitions import Machine


class PipelineMachine:
    states: ClassVar[list[str]] = [
        "created",
        "ingesting",
        "ingested",
        "planning",
        "planned",
        "rendering",
        "rendered",
        "visualizing",
        "visualized",
        "validating",
        "validated",
        "failed",
    ]

    transitions: ClassVar[list[dict[str, object]]] = [
        {"trigger": "ingest_started", "source": "created", "dest": "ingesting"},
        {"trigger": "ingest_completed", "source": "ingesting", "dest": "ingested"},
        {"trigger": "planning_started", "source": "ingested", "dest": "planning"},
        {"trigger": "planning_completed", "source": "planning", "dest": "planned"},
        {"trigger": "render_started", "source": "planned", "dest": "rendering"},
        {"trigger": "render_completed", "source": "rendering", "dest": "rendered"},
        {"trigger": "visualizing_started", "source": "rendered", "dest": "visualizing"},
        {"trigger": "visualizing_completed", "source": "visualizing", "dest": "visualized"},
        {"trigger": "validation_started", "source": "visualized", "dest": "validating"},
        {"trigger": "validation_completed", "source": "validating", "dest": "validated"},
        {"trigger": "fail", "source": "*", "dest": "failed"},
    ]

    def __init__(self) -> None:
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial="created",
            auto_transitions=False,
        )


class ToolCallMachine:
    states: ClassVar[list[str]] = [
        "idle",
        "received",
        "eliciting",
        "running",
        "progress",
        "completed",
        "tool_error",
        "fatal_error",
    ]

    transitions: ClassVar[list[dict[str, object]]] = [
        {"trigger": "receive", "source": "idle", "dest": "received"},
        {"trigger": "elicit", "source": "received", "dest": "eliciting"},
        {"trigger": "resume", "source": "eliciting", "dest": "running"},
        {"trigger": "start", "source": "received", "dest": "running"},
        {"trigger": "report_progress", "source": "running", "dest": "progress"},
        {"trigger": "complete", "source": ["running", "progress"], "dest": "completed"},
        {
            "trigger": "fail_tool",
            "source": ["received", "running", "progress"],
            "dest": "tool_error",
        },
        {"trigger": "fail_fatal", "source": "*", "dest": "fatal_error"},
    ]

    def __init__(self) -> None:
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial="idle",
            auto_transitions=False,
        )

"""Explicit, inspectable run state machine.

Implements the spec's state chain:

    INITIALIZE -> ANALYZE_INPUTS -> TEAM_LEAD_DESIGN
      -> (CYCLE_n_IMPLEMENT_AND_TEST -> TEAM_LEAD_REVIEW_n) * cycles_total
      -> TEAM_LEAD_FINAL_REVIEW -> FINAL_VALIDATION -> COMPLETE | FAILED

The fixed states are an enum; the per-cycle states are rendered as strings
from a loop over ``cycles_total`` so the machine reproduces the spec's exact
state names for the required ``cycles=3`` without hard-coding "3" into the
type itself.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from agentic_builder.events import atomic_write_json


class RunState(str, Enum):
    INITIALIZE = "INITIALIZE"
    ANALYZE_INPUTS = "ANALYZE_INPUTS"
    TEAM_LEAD_DESIGN = "TEAM_LEAD_DESIGN"
    TEAM_LEAD_FINAL_REVIEW = "TEAM_LEAD_FINAL_REVIEW"
    FINAL_VALIDATION = "FINAL_VALIDATION"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


def cycle_implement_state(cycle: int) -> str:
    return f"CYCLE_{cycle}_IMPLEMENT_AND_TEST"


def cycle_review_state(cycle: int) -> str:
    return f"TEAM_LEAD_REVIEW_{cycle}"


def state_sequence(cycles_total: int) -> list[str]:
    """The full ordered list of state names for a run with ``cycles_total`` cycles."""
    states: list[str] = [
        RunState.INITIALIZE.value,
        RunState.ANALYZE_INPUTS.value,
        RunState.TEAM_LEAD_DESIGN.value,
    ]
    for cycle in range(1, cycles_total + 1):
        states.append(cycle_implement_state(cycle))
        states.append(cycle_review_state(cycle))
    states.extend(
        [
            RunState.TEAM_LEAD_FINAL_REVIEW.value,
            RunState.FINAL_VALIDATION.value,
            RunState.COMPLETE.value,
        ]
    )
    return states


@dataclass
class RunStateDoc:
    """Persisted, resumable record of a single run's progress."""

    run_id: str
    cycles_total: int
    workspace: str
    input_dir: str
    input_manifest_hash: str
    current_state: str = RunState.INITIALIZE.value
    current_cycle: int = 0
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    history: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @staticmethod
    def new(
        cycles_total: int,
        workspace: str,
        input_dir: str,
        input_manifest_hash: str,
        run_id: str | None = None,
    ) -> RunStateDoc:
        return RunStateDoc(
            run_id=run_id or f"run-{uuid.uuid4().hex[:12]}",
            cycles_total=cycles_total,
            workspace=workspace,
            input_dir=input_dir,
            input_manifest_hash=input_manifest_hash,
        )

    def is_done(self, state_name: str) -> bool:
        return any(
            entry["state"] == state_name and entry["status"] == "done" for entry in self.history
        )

    def mark_done(self, state_name: str) -> None:
        self.history.append({"state": state_name, "status": "done", "timestamp": time.time()})
        self.current_state = state_name
        self.updated_at = time.time()

    def mark_failed(self, state_name: str, error: str) -> None:
        self.history.append(
            {"state": state_name, "status": "failed", "timestamp": time.time(), "error": error}
        )
        self.current_state = RunState.FAILED.value
        self.error = error
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "cycles_total": self.cycles_total,
            "workspace": self.workspace,
            "input_dir": self.input_dir,
            "input_manifest_hash": self.input_manifest_hash,
            "current_state": self.current_state,
            "current_cycle": self.current_cycle,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "history": self.history,
            "error": self.error,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RunStateDoc:
        return RunStateDoc(
            run_id=data["run_id"],
            cycles_total=data["cycles_total"],
            workspace=data["workspace"],
            input_dir=data["input_dir"],
            input_manifest_hash=data["input_manifest_hash"],
            current_state=data.get("current_state", RunState.INITIALIZE.value),
            current_cycle=data.get("current_cycle", 0),
            started_at=data.get("started_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            history=data.get("history", []),
            error=data.get("error"),
        )


def run_dir_for(runs_root: Path, run_id: str) -> Path:
    return runs_root / run_id


def state_path(run_dir: Path) -> Path:
    return run_dir / "state.json"


def save_state(run_dir: Path, doc: RunStateDoc) -> None:
    atomic_write_json(state_path(run_dir), doc.to_dict())


def load_state(run_dir: Path) -> RunStateDoc:
    import json

    data = json.loads(state_path(run_dir).read_text("utf-8"))
    return RunStateDoc.from_dict(data)

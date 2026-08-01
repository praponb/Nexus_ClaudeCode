"""QA test case and defect report shapes.

Field set matches the spec's "Each test case must have at least" list
verbatim so QA assets are structurally honest and comparable across cycles.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TestStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    MANUAL = "MANUAL"


class TestCase(BaseModel):
    test_id: str
    requirement_ids: list[str] = Field(default_factory=list)
    title: str
    objective: str
    priority: str
    type: str
    preconditions: str = ""
    test_data: str = ""
    steps: list[str] = Field(default_factory=list)
    expected_result: str
    actual_result: str = ""
    status: TestStatus = TestStatus.NOT_RUN
    automation_status: str = "manual"
    evidence_path: str = ""
    defect_id: str | None = None
    cycle_last_executed: int | None = None


class DefectReport(BaseModel):
    defect_id: str
    severity: str
    title: str
    requirement_ids: list[str] = Field(default_factory=list)
    reproduction_steps: list[str] = Field(default_factory=list)
    expected_result: str
    actual_result: str
    evidence_path: str = ""
    cycle_found: int

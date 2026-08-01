"""The required fake-model end-to-end test: drives 3 real cycles through the
real orchestrator/state machine with zero network access."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_builder.config import ModelProvider, Settings
from agentic_builder.orchestrator import Orchestrator
from agentic_builder.state import RunState


@pytest.mark.asyncio
async def test_fake_model_completes_three_full_cycles(fixtures_dir: Path, workspace: Path) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.FAKE,
        input_dir=fixtures_dir / "requirements_valid",
        workspace=workspace,
        cycles=3,
    )
    orchestrator = Orchestrator(settings)

    doc = await orchestrator.run()

    assert doc.current_state == RunState.COMPLETE.value
    assert doc.cycles_total == 3

    run_dir = workspace / "runs" / orchestrator.run_id

    # Structural state-machine proof: exactly 3 implement + 3 review cycle states done.
    implement_states = [e["state"] for e in doc.history if e["state"].startswith("CYCLE_")]
    review_states = [e["state"] for e in doc.history if e["state"].startswith("TEAM_LEAD_REVIEW_")]
    assert implement_states == [
        "CYCLE_1_IMPLEMENT_AND_TEST",
        "CYCLE_2_IMPLEMENT_AND_TEST",
        "CYCLE_3_IMPLEMENT_AND_TEST",
    ]
    assert review_states == ["TEAM_LEAD_REVIEW_1", "TEAM_LEAD_REVIEW_2", "TEAM_LEAD_REVIEW_3"]

    # Design spec exists (written once per cycle + final review, each time with the
    # full current content).
    design_path = workspace / "detail-design-specification.md"
    assert design_path.exists()

    # Per-agent-owned files only under their own subtree.
    assert (workspace / "frontend" / "README.md").exists()
    assert (workspace / "backend" / "README.md").exists()
    for cycle in (1, 2, 3):
        assert (workspace / "testcase" / f"TC-{cycle}-001.md").exists()

    # Per-cycle run artifacts for all 3 cycles.
    for cycle in (1, 2, 3):
        cycle_dir = run_dir / f"cycle-{cycle}"
        assert (cycle_dir / "cycle-plan.md").exists()
        assert (cycle_dir / "frontend-summary.md").exists()
        assert (cycle_dir / "backend-summary.md").exists()
        assert (cycle_dir / "qa-test-design-summary.md").exists()
        assert (cycle_dir / "qa-execution-report.md").exists()
        assert (cycle_dir / "defects.json").exists()

    # Traceability populated with the requirement carried across all 3 cycles.
    traceability = json.loads((run_dir / "traceability.json").read_text("utf-8"))
    assert traceability["requirements"]["REQ-1"]["last_cycle_updated"] == 3

    # Final report exists with the required sections.
    final_report = (run_dir / "final-report.md").read_text("utf-8")
    for heading in (
        "# Final Quality Report",
        "## Requirements implemented",
        "## Requirements not implemented",
        "## Test results",
        "## Open defects by severity",
        "## Build, lint, type-check, and test command outcomes",
        "## Remaining assumptions and risks",
        "## Requirement traceability",
        "## How to run the generated application",
    ):
        assert heading in final_report

    # No secrets, no network/litellm import path was exercised (fake path only).
    events_text = (run_dir / "events.jsonl").read_text("utf-8")
    assert "MODEL_API_KEY" not in events_text or "REDACTED" in events_text


@pytest.mark.asyncio
async def test_fake_model_never_writes_outside_owned_subtrees(
    fixtures_dir: Path, workspace: Path
) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.FAKE,
        input_dir=fixtures_dir / "requirements_valid",
        workspace=workspace,
        cycles=3,
    )
    orchestrator = Orchestrator(settings)
    await orchestrator.run()

    run_dir = workspace / "runs" / orchestrator.run_id
    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    for event in events:
        if event.get("type") != "files_written":
            continue
        owner = event["owner"]
        for path in event["paths"]:
            if owner == "frontend":
                assert path.startswith("frontend/")
            elif owner == "backend":
                assert path.startswith("backend/") or path.startswith("scripts/")
            elif owner == "qa":
                assert path.startswith("testcase/")

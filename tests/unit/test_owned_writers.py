from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentic_builder.errors import OwnershipViolationError
from agentic_builder.tools.owned_writers import (
    make_design_writer,
    make_files_writer,
    make_qa_execution_writer,
)


def _tool_context(
    workspace: Path, run_dir: Path, cycle: int = 1, dry_run: bool = False
) -> SimpleNamespace:
    return SimpleNamespace(
        state={
            "workspace": str(workspace),
            "run_dir": str(run_dir),
            "cycle": cycle,
            "dry_run": dry_run,
        }
    )


@pytest.mark.asyncio
async def test_files_writer_writes_within_owned_prefix(workspace: Path, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    writer = make_files_writer("frontend", ("frontend",), "frontend-summary.md")
    tool_context = _tool_context(workspace, run_dir)

    result = await writer(
        tool_context,
        files_json=json.dumps({"frontend/src/App.tsx": "export default {}"}),
        summary_markdown="# summary",
    )

    assert result["written"] == ["frontend/src/App.tsx"]
    assert (workspace / "frontend" / "src" / "App.tsx").read_text("utf-8") == "export default {}"
    assert (run_dir / "cycle-1" / "frontend-summary.md").read_text("utf-8") == "# summary"


@pytest.mark.asyncio
async def test_files_writer_rejects_path_outside_owned_prefix(
    workspace: Path, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    writer = make_files_writer("frontend", ("frontend",), "frontend-summary.md")
    tool_context = _tool_context(workspace, run_dir)

    with pytest.raises(OwnershipViolationError):
        await writer(
            tool_context,
            files_json=json.dumps({"backend/app.py": "print('sneaky')"}),
            summary_markdown="# summary",
        )
    assert not (workspace / "backend").exists()


@pytest.mark.asyncio
async def test_files_writer_dry_run_writes_nothing(workspace: Path, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    writer = make_files_writer("backend", ("backend", "scripts"), "backend-summary.md")
    tool_context = _tool_context(workspace, run_dir, dry_run=True)

    result = await writer(
        tool_context,
        files_json=json.dumps({"backend/main.py": "print('hi')"}),
        summary_markdown="# summary",
    )

    assert result["dry_run"] is True
    assert not (workspace / "backend").exists()
    assert not (run_dir / "cycle-1" / "backend-summary.md").exists()


@pytest.mark.asyncio
async def test_files_writer_allows_multiple_owned_prefixes(workspace: Path, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    writer = make_files_writer("backend", ("backend", "scripts"), "backend-summary.md")
    tool_context = _tool_context(workspace, run_dir)

    result = await writer(
        tool_context,
        files_json=json.dumps({"backend/app.py": "x", "scripts/migrate.sh": "y"}),
        summary_markdown="# summary",
    )
    assert set(result["written"]) == {"backend/app.py", "scripts/migrate.sh"}


@pytest.mark.asyncio
async def test_design_writer_writes_design_and_plan_and_traceability(
    workspace: Path, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    writer = make_design_writer()
    tool_context = _tool_context(workspace, run_dir, cycle=1)

    result = await writer(
        tool_context,
        design_markdown="# Design v1",
        cycle_plan_markdown="# Plan cycle 1",
        requirements_json=json.dumps(
            [
                {
                    "req_id": "REQ-1",
                    "description": "desc",
                    "source_file": "specification.md",
                    "status": "designed",
                }
            ]
        ),
    )

    assert (workspace / "detail-design-specification.md").read_text("utf-8") == "# Design v1"
    assert (run_dir / "cycle-1" / "cycle-plan.md").read_text("utf-8") == "# Plan cycle 1"
    traceability = json.loads((run_dir / "traceability.json").read_text("utf-8"))
    assert traceability["requirements"]["REQ-1"]["last_cycle_updated"] == 1
    assert result["requirement_count"] == 1


@pytest.mark.asyncio
async def test_design_writer_ignores_dry_run(workspace: Path, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    writer = make_design_writer()
    tool_context = _tool_context(workspace, run_dir, cycle=1, dry_run=True)

    await writer(
        tool_context,
        design_markdown="# Design v1",
        cycle_plan_markdown="# Plan cycle 1",
        requirements_json="[]",
    )

    # The design/plan is the artifact --dry-run is meant to let a user inspect,
    # so it must be written even when dry_run is set.
    assert (workspace / "detail-design-specification.md").exists()


@pytest.mark.asyncio
async def test_qa_execution_writer_records_results_and_defects(
    workspace: Path, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    (workspace / "testcase").mkdir(parents=True)
    writer = make_qa_execution_writer()
    tool_context = _tool_context(workspace, run_dir, cycle=2)

    await writer(
        tool_context,
        execution_report_markdown="# QA report",
        results_json=json.dumps(
            [{"test_id": "TC-2-001", "status": "FAILED", "actual_result": "boom"}]
        ),
        defects_json=json.dumps([{"defect_id": "D-1", "severity": "high", "title": "bug"}]),
    )

    assert (run_dir / "cycle-2" / "qa-execution-report.md").read_text("utf-8") == "# QA report"
    defects = json.loads((run_dir / "cycle-2" / "defects.json").read_text("utf-8"))
    assert defects[0]["defect_id"] == "D-1"
    status = json.loads((workspace / "testcase" / "execution-status.json").read_text("utf-8"))
    assert status["TC-2-001"]["status"] == "FAILED"
    assert status["TC-2-001"]["cycle_last_executed"] == 2

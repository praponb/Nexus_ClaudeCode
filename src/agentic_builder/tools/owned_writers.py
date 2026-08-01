"""Write tools enforcing each agent's disjoint write ownership.

Ownership map (spec's "Concurrency and File-Safety Rules"):
  - Team Lead  -> ``detail-design-specification.md`` + cycle plans
  - Frontend   -> ``frontend/``
  - Backend    -> ``backend/`` and ``scripts/`` (see ASSUMPTIONS.md)
  - QA         -> ``testcase/``

Each writer only accepts paths under its own agent's allowed prefixes, even
if a tool were ever mistakenly wired to the wrong agent, and honors
``dry_run`` by returning a preview instead of writing.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from agentic_builder.errors import OwnershipViolationError
from agentic_builder.events import append_event, atomic_write_json, atomic_write_text
from agentic_builder.tools.workspace import resolve_within

ToolFunc = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


def _is_allowed(relative_path: str, allowed_prefixes: tuple[str, ...]) -> bool:
    normalized = relative_path.strip("/")
    return any(normalized == p or normalized.startswith(p + "/") for p in allowed_prefixes)


def make_files_writer(
    owner: str,
    allowed_prefixes: tuple[str, ...],
    summary_filename: str,
    tool_name: str | None = None,
) -> ToolFunc:
    """Build a files-writer tool confined to ``allowed_prefixes``.

    Defaults to ``write_<owner>_files`` as the tool's callable name; pass
    ``tool_name`` explicitly when the owner and the tool's public name
    differ (e.g. QA's ``testcase/`` writer is named ``write_testcase_files``).
    """

    async def write_owned_files(
        tool_context: Any, files_json: str, summary_markdown: str
    ) -> dict[str, Any]:
        """Write one or more files and this cycle's summary.

        Args:
          files_json: JSON object mapping each relative file path (must be
            under this agent's owned directory) to its full file content.
          summary_markdown: Cycle summary containing changed files, commands
            run, results, assumptions, and known issues.
        """
        workspace = Path(tool_context.state["workspace"])
        run_dir = Path(tool_context.state["run_dir"])
        cycle = int(tool_context.state["cycle"])
        dry_run = bool(tool_context.state.get("dry_run", False))

        try:
            files = json.loads(files_json)
        except json.JSONDecodeError as exc:
            return {"error": f"files_json is not valid JSON: {exc}"}
        if not isinstance(files, dict):
            return {"error": "files_json must decode to an object of relative_path -> content"}

        resolved: list[tuple[str, Path, str]] = []
        for rel_path, content in files.items():
            if not _is_allowed(rel_path, allowed_prefixes):
                raise OwnershipViolationError(
                    f"{owner} is not permitted to write {rel_path!r}; "
                    f"allowed prefixes: {allowed_prefixes}"
                )
            resolved.append((rel_path, resolve_within(workspace, rel_path), str(content)))

        summary_path = run_dir / f"cycle-{cycle}" / summary_filename

        if dry_run:
            paths = [r for r, _, _ in resolved] + [str(summary_path)]
            append_event(
                run_dir,
                {"type": "would_write", "owner": owner, "cycle": cycle, "paths": paths},
            )
            return {"dry_run": True, "would_write": [r for r, _, _ in resolved]}

        written: list[str] = []
        for rel_path, abs_path, content in resolved:
            atomic_write_text(abs_path, content)
            written.append(rel_path)
        atomic_write_text(summary_path, summary_markdown)

        append_event(
            run_dir,
            {"type": "files_written", "owner": owner, "cycle": cycle, "paths": written},
        )
        return {"written": written, "summary_path": str(summary_path)}

    write_owned_files.__name__ = tool_name or f"write_{owner}_files"
    return write_owned_files


def make_design_writer() -> ToolFunc:
    """Build the Team Lead's ``publish_design_and_plan`` tool.

    Unlike the generic owned-files writer, this tool writes to fixed,
    hard-coded paths (never agent-supplied), so no path-prefix check is
    needed for the design doc / cycle plan themselves. It also ignores
    ``dry_run``: the whole point of ``--dry-run`` is to let a user inspect
    the design and cycle plan the Team Lead would produce, so those writes
    always happen even in dry-run mode. Only the generated-application
    writers below (frontend/backend/testcase) and command execution
    short-circuit to a preview in dry-run.
    """

    async def publish_design_and_plan(
        tool_context: Any,
        design_markdown: str,
        cycle_plan_markdown: str,
        requirements_json: str,
    ) -> dict[str, Any]:
        """Publish the revised detailed design spec, this cycle's plan, and
        requirement traceability updates.

        Args:
          design_markdown: The full, current content of
            ``detail-design-specification.md``, including an appended
            revision-history entry for this cycle.
          cycle_plan_markdown: This cycle's plan for the Frontend, Backend,
            and QA agents.
          requirements_json: JSON array of requirement objects, each with at
            least ``req_id``, ``description``, ``source_file``, ``status``,
            and optionally ``design_ref``, ``implementing_files``,
            ``test_ids``.
        """
        workspace = Path(tool_context.state["workspace"])
        run_dir = Path(tool_context.state["run_dir"])
        cycle = int(tool_context.state["cycle"])

        try:
            requirements = json.loads(requirements_json)
        except json.JSONDecodeError as exc:
            return {"error": f"requirements_json is not valid JSON: {exc}"}
        if not isinstance(requirements, list):
            return {"error": "requirements_json must decode to an array of requirement objects"}

        design_path = resolve_within(workspace, "detail-design-specification.md")
        plan_path = run_dir / f"cycle-{cycle}" / "cycle-plan.md"
        traceability_path = run_dir / "traceability.json"

        atomic_write_text(design_path, design_markdown)
        atomic_write_text(plan_path, cycle_plan_markdown)

        existing: dict[str, Any] = (
            json.loads(traceability_path.read_text("utf-8"))
            if traceability_path.exists()
            else {"requirements": {}}
        )
        for req in requirements:
            req_id = req.get("req_id") if isinstance(req, dict) else None
            if not req_id:
                continue
            req = dict(req)
            req["last_cycle_updated"] = cycle
            existing["requirements"][req_id] = req
        atomic_write_json(traceability_path, existing)

        append_event(
            run_dir,
            {
                "type": "design_published",
                "owner": "team_lead",
                "cycle": cycle,
                "requirement_count": len(requirements),
            },
        )
        return {
            "design_path": str(design_path),
            "cycle_plan_path": str(plan_path),
            "requirement_count": len(requirements),
        }

    return publish_design_and_plan


def make_qa_execution_writer() -> ToolFunc:
    """Build QA's ``write_qa_execution_report`` tool (execution phase only)."""

    async def write_qa_execution_report(
        tool_context: Any,
        execution_report_markdown: str,
        results_json: str,
        defects_json: str,
    ) -> dict[str, Any]:
        """Record QA execution results, an execution report, and any defects.

        Args:
          execution_report_markdown: Human-readable summary of what was run
            and the outcome.
          results_json: JSON array of test result updates, each with at
            least ``test_id`` and ``status`` (one of NOT_RUN, PASSED, FAILED,
            BLOCKED, MANUAL), plus ``actual_result``, ``evidence_path``,
            ``defect_id`` where applicable. A test must never be marked
            PASSED unless it was actually executed with captured evidence.
          defects_json: JSON array of defect report objects.
        """
        workspace = Path(tool_context.state["workspace"])
        run_dir = Path(tool_context.state["run_dir"])
        cycle = int(tool_context.state["cycle"])
        dry_run = bool(tool_context.state.get("dry_run", False))

        try:
            results = json.loads(results_json)
            defects = json.loads(defects_json)
        except json.JSONDecodeError as exc:
            return {"error": f"results_json/defects_json is not valid JSON: {exc}"}

        cycle_dir = run_dir / f"cycle-{cycle}"
        report_path = cycle_dir / "qa-execution-report.md"
        defects_path = cycle_dir / "defects.json"
        status_path = resolve_within(workspace, "testcase/execution-status.json")

        if dry_run:
            append_event(
                run_dir,
                {
                    "type": "would_write",
                    "owner": "qa",
                    "cycle": cycle,
                    "paths": [str(report_path), str(defects_path), str(status_path)],
                },
            )
            return {"dry_run": True}

        atomic_write_text(report_path, execution_report_markdown)
        atomic_write_json(defects_path, defects)

        existing_status: dict[str, Any] = (
            json.loads(status_path.read_text("utf-8")) if status_path.exists() else {}
        )
        for result in results:
            test_id = result.get("test_id") if isinstance(result, dict) else None
            if not test_id:
                continue
            result = dict(result)
            result["cycle_last_executed"] = cycle
            existing_status[test_id] = result
        atomic_write_json(status_path, existing_status)

        append_event(
            run_dir,
            {
                "type": "qa_execution_recorded",
                "owner": "qa",
                "cycle": cycle,
                "result_count": len(results),
                "defect_count": len(defects),
            },
        )
        return {
            "report_path": str(report_path),
            "defects_path": str(defects_path),
            "status_path": str(status_path),
        }

    return write_qa_execution_report

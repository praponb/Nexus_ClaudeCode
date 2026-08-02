"""The three-cycle design/implement/QA orchestrator.

Drives the explicit state machine in ``state.py``. Frontend, Backend, and QA
test-design run concurrently within each cycle (``asyncio.gather`` over
independent agent invocations); QA execution runs afterward, once
frontend/backend deliverables for that cycle exist. A QA test failure is
recorded as data and never aborts the run. An agent picking an unavailable
command or malformed tool arguments is also non-fatal -- those tools return
a structured ``{"error": ...}`` result the model can recover from, rather
than raising (raising inside one of several concurrently-gathered agent
invocations would cancel its unrelated siblings' legitimate work too). Only
genuine setup-level failures (path/ownership violations, model-resolution
errors, or any other unexpected exception) transition the run to FAILED.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import InMemoryRunner
from google.genai import types

from agentic_builder.agents import (
    build_backend_agent,
    build_frontend_agent,
    build_qa_agent,
    build_team_lead_agent,
)
from agentic_builder.config import Settings, mask_secrets
from agentic_builder.errors import FatalOrchestrationError, InputValidationError
from agentic_builder.events import append_event, atomic_write_json, atomic_write_text
from agentic_builder.logging import log_event
from agentic_builder.models.provider import build_llm
from agentic_builder.schemas.traceability import RequirementRecord, TraceabilityMatrix
from agentic_builder.state import (
    RunState,
    RunStateDoc,
    cycle_implement_state,
    cycle_review_state,
    load_state,
    run_dir_for,
    save_state,
    state_path,
)
from agentic_builder.tools.markdown_discovery import InputManifest, load_and_validate_inputs

StateHandler = Callable[[], Awaitable[None]]

#: RequirementRecord.status is a free-text field the Team Lead sets (see
#: prompts/team_lead.md), not a closed enum -- match case-insensitively
#: against every synonym actually observed in real runs (e.g. "verified"),
#: not just "implemented"/"tested", so the final report's implemented/
#: not-implemented split doesn't miscategorize genuinely completed work.
_IMPLEMENTED_STATUSES = frozenset(
    {"implemented", "tested", "verified", "done", "complete", "completed"}
)


class Orchestrator:
    """Owns run state, agent invocation, and consolidated reports for one run."""

    APP_NAME = "agentic_builder"

    def __init__(self, settings: Settings, run_id: str | None = None) -> None:
        self.settings = settings
        self.workspace = Path(settings.workspace).resolve()
        self.input_dir = Path(settings.input_dir).resolve()
        self.runs_root = self.workspace / "runs"
        self.cycles_total = settings.cycles
        self.dry_run = settings.dry_run
        self.run_id = run_id
        self.run_dir: Path = self.runs_root
        self.current_cycle = 0
        self._current_state_name: str | None = None
        self.state_doc: RunStateDoc | None = None
        self._manifest: InputManifest | None = None

        # Real models (esp. kimi-k3, which always runs in extended thinking
        # mode) can take minutes to produce a large response. Non-streaming
        # calls buffer the *entire* response before sending any bytes back,
        # which is exactly the shape of request an idle-connection timeout
        # somewhere in the network path (proxy, load balancer, etc.) will
        # silently kill -- confirmed in practice against the live Moonshot
        # API: a ~15KB non-streaming completion never returned, the
        # identical request streamed completed in ~5 minutes with the first
        # byte arriving in ~2s. SSE streaming avoids that failure mode.
        self._run_config = RunConfig(streaming_mode=StreamingMode.SSE)

        timeout = settings.agent_timeout_seconds
        self._agents = {
            "team_lead": build_team_lead_agent(build_llm(settings, "team_lead"), timeout=timeout),
            "frontend": build_frontend_agent(build_llm(settings, "frontend"), timeout=timeout),
            "backend": build_backend_agent(build_llm(settings, "backend"), timeout=timeout),
            "qa": build_qa_agent(build_llm(settings, "qa"), timeout=timeout),
        }
        self._runners = {
            role: InMemoryRunner(agent=agent, app_name=self.APP_NAME)
            for role, agent in self._agents.items()
        }

    # -- top-level run/resume ------------------------------------------------

    async def run(self, resume: bool = False) -> RunStateDoc:
        try:
            manifest = load_and_validate_inputs(self.input_dir)
        except InputValidationError as exc:
            raise FatalOrchestrationError(str(exc)) from exc
        self._manifest = manifest

        if resume:
            if not self.run_id:
                raise FatalOrchestrationError("Resuming a run requires --run-id.")
            self.run_dir = run_dir_for(self.runs_root, self.run_id)
            if not state_path(self.run_dir).exists():
                raise FatalOrchestrationError(f"No such run to resume: {self.run_id!r}")
            self.state_doc = load_state(self.run_dir)
            if self.state_doc.input_manifest_hash != manifest.combined_hash:
                raise FatalOrchestrationError(
                    f"Input requirement files under {self.input_dir} have changed since "
                    f"run {self.run_id} started; refusing to resume against drifted input. "
                    "Start a new run instead."
                )
            self.cycles_total = self.state_doc.cycles_total
        else:
            self.state_doc = RunStateDoc.new(
                cycles_total=self.cycles_total,
                workspace=str(self.workspace),
                input_dir=str(self.input_dir),
                input_manifest_hash=manifest.combined_hash,
                run_id=self.run_id,
            )
            self.run_id = self.state_doc.run_id
            self.run_dir = run_dir_for(self.runs_root, self.run_id)
            save_state(self.run_dir, self.state_doc)

        self._log_and_record(
            {"type": "run_resumed" if resume else "run_started", "run_id": self.run_id}
        )

        try:
            await self._run_state(RunState.INITIALIZE.value, self._state_initialize)
            await self._run_state(RunState.ANALYZE_INPUTS.value, self._state_analyze_inputs)
            await self._run_state(
                RunState.TEAM_LEAD_DESIGN.value, self._make_team_lead_handler(1, "initial_design")
            )
            for cycle in range(1, self.cycles_total + 1):
                await self._run_state(cycle_implement_state(cycle), self._make_cycle_handler(cycle))
                await self._run_state(
                    cycle_review_state(cycle), self._make_team_lead_handler(cycle, "review")
                )
            await self._run_state(
                RunState.TEAM_LEAD_FINAL_REVIEW.value,
                self._make_team_lead_handler(self.cycles_total, "final_review"),
            )
            await self._run_state(RunState.FINAL_VALIDATION.value, self._state_final_validation)

            assert self.state_doc is not None
            self.state_doc.mark_done(RunState.COMPLETE.value)
            save_state(self.run_dir, self.state_doc)
            self._log_and_record({"type": "run_complete", "run_id": self.run_id})
        except FatalOrchestrationError as exc:
            assert self.state_doc is not None
            # Use the state that was actually executing when it failed, not
            # self.state_doc.current_state (which only reflects the last
            # *successfully completed* state -- mark_done() is what updates
            # it, and that never runs for the state that raised).
            failed_state = self._current_state_name or self.state_doc.current_state
            self.state_doc.mark_failed(failed_state, mask_secrets(str(exc), self.settings))
            save_state(self.run_dir, self.state_doc)
            self._log_and_record(
                {"type": "run_failed", "error": mask_secrets(str(exc), self.settings)}
            )
            raise

        return self.state_doc

    # -- state machine plumbing ----------------------------------------------

    async def _run_state(self, state_name: str, handler: StateHandler) -> None:
        assert self.state_doc is not None
        if self.state_doc.is_done(state_name):
            self._log_and_record({"type": "state_skipped_resume", "state": state_name})
            return
        self._current_state_name = state_name
        self._log_and_record({"type": "state_entered", "state": state_name})
        try:
            await handler()
        except FatalOrchestrationError:
            raise
        except Exception as exc:  # noqa: BLE001 -- any other exception is a fatal setup error
            raise FatalOrchestrationError(f"Fatal error in state {state_name}: {exc}") from exc
        self.state_doc.mark_done(state_name)
        save_state(self.run_dir, self.state_doc)
        self._log_and_record({"type": "state_done", "state": state_name})

    def _log_and_record(self, event: dict[str, Any]) -> None:
        append_event(self.run_dir, event, self.settings)
        log_event(event, verbose=self.settings.verbose, settings=self.settings)

    def _make_cycle_handler(self, cycle: int) -> StateHandler:
        async def handler() -> None:
            await self._state_cycle_implement_and_test(cycle)

        return handler

    def _make_team_lead_handler(self, cycle: int, mode: str) -> StateHandler:
        async def handler() -> None:
            await self._state_team_lead(cycle, mode)

        return handler

    # -- agent invocation -----------------------------------------------------

    async def _invoke_agent(self, role: str, user_text: str) -> str:
        runner = self._runners[role]
        session_id = f"{self.run_id}-{role}"
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id="orchestrator", session_id=session_id
        )
        if session is None:
            await runner.session_service.create_session(
                app_name=runner.app_name, user_id="orchestrator", session_id=session_id
            )
        state_delta = {
            "input_dir": str(self.input_dir),
            "workspace": str(self.workspace),
            "run_dir": str(self.run_dir),
            "cycle": self.current_cycle,
            "dry_run": self.dry_run,
        }
        final_text = ""
        async for event in runner.run_async(
            user_id="orchestrator",
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=user_text)]),
            state_delta=state_delta,
            run_config=self._run_config,
        ):
            if event.content and event.content.parts:
                text_parts = [part.text for part in event.content.parts if part.text]
                if text_parts:
                    final_text = "".join(text_parts)
        return final_text

    # -- individual states ----------------------------------------------------

    async def _state_initialize(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("frontend", "backend", "testcase", "scripts"):
            (self.workspace / sub).mkdir(parents=True, exist_ok=True)
        for cycle in range(1, self.cycles_total + 1):
            (self.run_dir / f"cycle-{cycle}").mkdir(parents=True, exist_ok=True)

    async def _state_analyze_inputs(self) -> None:
        assert self._manifest is not None
        atomic_write_json(self.run_dir / "input-manifest.json", self._manifest.model_dump())

    async def _state_team_lead(self, cycle: int, mode: str) -> None:
        self.current_cycle = cycle
        if mode == "initial_design":
            user_text = (
                f"Cycle: {cycle}\nMode: initial_design\n\n"
                "This is the first design cycle. Use discover_markdown_files and "
                "read_markdown_file to read every requirement file, then call "
                "publish_design_and_plan with the initial detail-design-specification.md "
                "and the cycle 1 plan."
            )
        elif mode == "review":
            run_prefix = f"runs/{self.run_id}/cycle-{cycle}"
            user_text = (
                f"Cycle: {cycle}\nMode: review\n\n"
                f"Review cycle {cycle}'s deliverables via read_workspace_file: "
                f"{run_prefix}/frontend-summary.md, {run_prefix}/backend-summary.md, "
                f"{run_prefix}/qa-test-design-summary.md, {run_prefix}/qa-execution-report.md, "
                f"and {run_prefix}/defects.json. Then call publish_design_and_plan with the "
                f"revised detail-design-specification.md (including a new revision-history "
                f"entry for cycle {cycle}) and the plan for the next cycle."
            )
        else:  # final_review
            user_text = (
                f"Cycle: {cycle}\nMode: final_review\n\n"
                "This is the final review after all cycles are complete. Read all cycle "
                "summaries and QA reports, then call publish_design_and_plan one last time "
                "with the fully finalized detail-design-specification.md (a final "
                "revision-history entry confirming Definition of Done status) and a short "
                "closing note."
            )
        result = await self._invoke_agent("team_lead", user_text)
        self._log_and_record(
            {
                "type": "agent_result",
                "role": "team_lead",
                "cycle": cycle,
                "mode": mode,
                "preview": result[:200],
            }
        )

    async def _state_cycle_implement_and_test(self, cycle: int) -> None:
        self.current_cycle = cycle
        plan_ref = f"runs/{self.run_id}/cycle-{cycle}/cycle-plan.md"

        frontend_text = (
            f"Cycle: {cycle}\n\nRead detail-design-specification.md and this cycle's plan "
            f"({plan_ref}) via read_workspace_file, then implement/update the frontend and "
            "call write_frontend_files."
        )
        backend_text = (
            f"Cycle: {cycle}\n\nRead detail-design-specification.md and this cycle's plan "
            f"({plan_ref}) via read_workspace_file, then implement/update the backend and "
            "call write_backend_files."
        )
        qa_design_text = (
            f"Cycle: {cycle}\nPhase: design\n\nRead detail-design-specification.md and this "
            f"cycle's plan ({plan_ref}) via read_workspace_file, then author/update test "
            "cases and call write_testcase_files."
        )

        frontend_result, backend_result, qa_design_result = await asyncio.gather(
            self._invoke_agent("frontend", frontend_text),
            self._invoke_agent("backend", backend_text),
            self._invoke_agent("qa", qa_design_text),
        )
        self._log_and_record(
            {
                "type": "cycle_implementation_complete",
                "cycle": cycle,
                "frontend_preview": frontend_result[:200],
                "backend_preview": backend_result[:200],
                "qa_design_preview": qa_design_result[:200],
            }
        )

        qa_execute_text = (
            f"Cycle: {cycle}\nPhase: execute\n\nFrontend and backend deliverables for this "
            "cycle are ready. Execute the automatable test cases under testcase/ using "
            "run_allowlisted_command where applicable, then call write_qa_execution_report "
            "with honest results and any defects. A failed test is expected data -- never "
            "mark it PASSED unless it actually ran."
        )
        qa_execution_result = await self._invoke_agent("qa", qa_execute_text)
        self._log_and_record(
            {"type": "qa_execution_complete", "cycle": cycle, "preview": qa_execution_result[:200]}
        )

    async def _state_final_validation(self) -> None:
        report_path = self.run_dir / "final-report.md"

        traceability = TraceabilityMatrix()
        traceability_path = self.run_dir / "traceability.json"
        if traceability_path.exists():
            raw = json.loads(traceability_path.read_text("utf-8"))
            traceability = TraceabilityMatrix(
                requirements={
                    req_id: RequirementRecord(**record)
                    for req_id, record in raw.get("requirements", {}).items()
                }
            )

        test_statuses: dict[str, Any] = {}
        test_status_path = self.workspace / "testcase" / "execution-status.json"
        if test_status_path.exists():
            test_statuses = json.loads(test_status_path.read_text("utf-8"))
        status_counts: dict[str, int] = {}
        for result in test_statuses.values():
            status = str(result.get("status", "NOT_RUN"))
            status_counts[status] = status_counts.get(status, 0) + 1

        defects: list[dict[str, Any]] = []
        for cycle in range(1, self.cycles_total + 1):
            defects_path = self.run_dir / f"cycle-{cycle}" / "defects.json"
            if defects_path.exists():
                defects.extend(json.loads(defects_path.read_text("utf-8")))
        open_defects_by_severity: dict[str, int] = {}
        for defect in defects:
            severity = str(defect.get("severity", "unknown"))
            open_defects_by_severity[severity] = open_defects_by_severity.get(severity, 0) + 1

        commands: list[dict[str, Any]] = []
        events_path = self.run_dir / "events.jsonl"
        if events_path.exists():
            for line in events_path.read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("type") == "command_executed":
                    commands.append(record)

        implemented = [
            r
            for r in traceability.requirements.values()
            if r.status.strip().lower() in _IMPLEMENTED_STATUSES
        ]
        not_implemented = [
            r
            for r in traceability.requirements.values()
            if r.status.strip().lower() not in _IMPLEMENTED_STATUSES
        ]

        lines = [
            "# Final Quality Report",
            "",
            f"Run: {self.run_id}",
            f"Cycles completed: {self.cycles_total}",
            "",
            "## Requirements implemented",
            "\n".join(f"- {r.req_id}: {r.description}" for r in implemented) or "- none recorded",
            "",
            "## Requirements not implemented",
            "\n".join(f"- {r.req_id}: {r.description} (status={r.status})" for r in not_implemented)
            or "- none",
            "",
            "## Test results",
            "\n".join(f"- {status}: {count}" for status, count in sorted(status_counts.items()))
            or "- no tests recorded",
            "",
            "## Open defects by severity",
            "\n".join(
                f"- {sev}: {count}" for sev, count in sorted(open_defects_by_severity.items())
            )
            or "- none",
            "",
            "## Build, lint, type-check, and test command outcomes",
            "\n".join(
                f"- cycle {c.get('cycle')}: {c.get('command_key')} -> exit {c.get('returncode')} "
                f"(timed_out={c.get('timed_out')})"
                for c in commands
            )
            or "- no commands executed",
            "",
            "## Remaining assumptions and risks",
            "See ASSUMPTIONS.md at the repository root.",
            "",
            "## Requirement traceability",
            traceability.to_markdown_table(),
            "",
            "## How to run the generated application",
            f"See frontend/README.md and backend/README.md under the workspace "
            f"({self.workspace}) for exact steps, as written by the Frontend and Backend "
            "agents during this run.",
        ]
        atomic_write_text(report_path, "\n".join(lines))
        self._log_and_record({"type": "final_report_written", "path": str(report_path)})

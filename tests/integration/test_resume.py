from __future__ import annotations

from pathlib import Path

import pytest

from agentic_builder.config import ModelProvider, Settings
from agentic_builder.errors import FatalOrchestrationError
from agentic_builder.orchestrator import Orchestrator
from agentic_builder.state import RunState


@pytest.mark.asyncio
async def test_resume_continues_after_simulated_crash_without_redoing_completed_cycles(
    fixtures_dir: Path, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.FAKE,
        input_dir=fixtures_dir / "requirements_valid",
        workspace=workspace,
        cycles=3,
    )
    orchestrator = Orchestrator(settings)

    original = Orchestrator._state_cycle_implement_and_test

    async def boom(self: Orchestrator, cycle: int) -> None:
        if cycle == 2:
            raise RuntimeError("simulated crash")
        await original(self, cycle)

    monkeypatch.setattr(Orchestrator, "_state_cycle_implement_and_test", boom)

    with pytest.raises(FatalOrchestrationError):
        await orchestrator.run()

    run_id = orchestrator.run_id
    assert run_id is not None
    run_dir = workspace / "runs" / run_id

    cycle1_summary_path = run_dir / "cycle-1" / "frontend-summary.md"
    assert cycle1_summary_path.exists()
    mtime_before_resume = cycle1_summary_path.stat().st_mtime_ns

    monkeypatch.setattr(Orchestrator, "_state_cycle_implement_and_test", original)

    # A fresh Orchestrator instance simulates resuming in a new process.
    resumed = Orchestrator(settings, run_id=run_id)
    doc = await resumed.run(resume=True)

    assert doc.current_state == RunState.COMPLETE.value
    # Cycle 1's artifacts were not rewritten on resume (that state was already done).
    assert cycle1_summary_path.stat().st_mtime_ns == mtime_before_resume
    for cycle in (1, 2, 3):
        assert (run_dir / f"cycle-{cycle}" / "qa-execution-report.md").exists()


@pytest.mark.asyncio
async def test_resume_refuses_when_input_files_have_changed(
    fixtures_dir: Path, workspace: Path, tmp_path: Path
) -> None:
    input_dir = tmp_path / "reqs"
    input_dir.mkdir()
    for name in ("specification.md", "layout.md", "front-back-end-stack.md"):
        (input_dir / name).write_text("v1", encoding="utf-8")

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.FAKE,
        input_dir=input_dir,
        workspace=workspace,
        cycles=3,
    )
    orchestrator = Orchestrator(settings)

    from agentic_builder.orchestrator import Orchestrator as OrchestratorClass

    async def boom(self: OrchestratorClass, cycle: int) -> None:
        raise RuntimeError("simulated crash")

    import pytest as _pytest

    with _pytest.MonkeyPatch.context() as mp:
        mp.setattr(OrchestratorClass, "_state_cycle_implement_and_test", boom)
        with pytest.raises(FatalOrchestrationError):
            await orchestrator.run()

    run_id = orchestrator.run_id
    (input_dir / "specification.md").write_text(
        "v2 -- changed after the run started", encoding="utf-8"
    )

    resumed = Orchestrator(settings, run_id=run_id)
    with pytest.raises(FatalOrchestrationError, match="changed since"):
        await resumed.run(resume=True)

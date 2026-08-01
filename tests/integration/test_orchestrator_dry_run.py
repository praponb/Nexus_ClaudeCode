from __future__ import annotations

from pathlib import Path

import pytest

from agentic_builder.config import ModelProvider, Settings
from agentic_builder.orchestrator import Orchestrator
from agentic_builder.state import RunState


@pytest.mark.asyncio
async def test_dry_run_writes_design_but_not_generated_app(
    fixtures_dir: Path, workspace: Path
) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.FAKE,
        input_dir=fixtures_dir / "requirements_valid",
        workspace=workspace,
        cycles=3,
        dry_run=True,
    )
    orchestrator = Orchestrator(settings)
    doc = await orchestrator.run()

    assert doc.current_state == RunState.COMPLETE.value
    # The design/plan is the thing --dry-run lets a user inspect: it is written.
    assert (workspace / "detail-design-specification.md").exists()

    # Generated-application directories must remain untouched.
    assert list((workspace / "frontend").iterdir()) == []
    assert list((workspace / "backend").iterdir()) == []
    assert list((workspace / "testcase").iterdir()) == []

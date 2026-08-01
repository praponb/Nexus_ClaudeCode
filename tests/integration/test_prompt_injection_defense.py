"""Prompt-injection defense: adversarial content in a requirement file must
never cause a write outside the reading agent's owned subtree, and must
reach the model only wrapped as inert, delimited data."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentic_builder.config import ModelProvider, Settings
from agentic_builder.orchestrator import Orchestrator
from agentic_builder.state import RunState
from agentic_builder.tools.markdown_discovery import read_markdown_file


@pytest.mark.asyncio
async def test_adversarial_file_content_is_wrapped_as_untrusted(fixtures_dir: Path) -> None:
    input_dir = fixtures_dir / "requirements_prompt_injection"
    tool_context = SimpleNamespace(state={"input_dir": str(input_dir)})
    result = await read_markdown_file(tool_context, "specification.md")
    assert "BEGIN UNTRUSTED DATA" in result["content"]
    assert "END UNTRUSTED DATA" in result["content"]
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in result["content"]  # present, but delimited


@pytest.mark.asyncio
async def test_run_against_adversarial_fixture_stays_within_ownership_boundaries(
    fixtures_dir: Path, workspace: Path
) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.FAKE,
        input_dir=fixtures_dir / "requirements_prompt_injection",
        workspace=workspace,
        cycles=3,
    )
    orchestrator = Orchestrator(settings)
    doc = await orchestrator.run()

    assert doc.current_state == RunState.COMPLETE.value

    # The adversarial spec asked for a file under backend/ written by the
    # frontend agent, and for a raw shell command instead of an allowlisted
    # key. Neither happened: only legitimate, owned files exist.
    assert not (workspace / "backend" / "secrets.txt").exists()

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

    # The adversarial text never appears in events.jsonl outside of the
    # markdown discovery/read events where it is expected as quoted data.
    events_text = (run_dir / "events.jsonl").read_text("utf-8")
    assert "MODEL_API_KEY" not in events_text

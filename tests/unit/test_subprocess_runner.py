from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentic_builder.errors import CommandNotAllowlistedError
from agentic_builder.tools.subprocess_runner import ALLOWLIST, run_allowlisted_command


def _tool_context(workspace: Path, run_dir: Path, dry_run: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        state={"workspace": str(workspace), "run_dir": str(run_dir), "cycle": 1, "dry_run": dry_run}
    )


@pytest.mark.asyncio
async def test_rejects_command_not_on_allowlist(workspace: Path, tmp_path: Path) -> None:
    tool_context = _tool_context(workspace, tmp_path / "run")
    with pytest.raises(CommandNotAllowlistedError):
        await run_allowlisted_command(tool_context, "rm -rf /")


@pytest.mark.asyncio
async def test_rejects_unsafe_extra_args(workspace: Path, tmp_path: Path) -> None:
    tool_context = _tool_context(workspace, tmp_path / "run")
    with pytest.raises(CommandNotAllowlistedError):
        await run_allowlisted_command(
            tool_context, "pytest", extra_args_json=json.dumps(["; rm -rf /"])
        )


@pytest.mark.asyncio
async def test_dry_run_does_not_execute(workspace: Path, tmp_path: Path) -> None:
    tool_context = _tool_context(workspace, tmp_path / "run", dry_run=True)
    result = await run_allowlisted_command(tool_context, "pytest")
    assert result["dry_run"] is True
    assert result["argv"] == ALLOWLIST["pytest"]


@pytest.mark.asyncio
async def test_runs_allowlisted_command_and_captures_output(
    workspace: Path, tmp_path: Path
) -> None:
    ALLOWLIST["_test_echo"] = [sys.executable, "-c", "print('hello-from-allowlist')"]
    try:
        tool_context = _tool_context(workspace, tmp_path / "run")
        result = await run_allowlisted_command(tool_context, "_test_echo")
        assert result["returncode"] == 0
        assert "hello-from-allowlist" in result["stdout"]
        assert result["timed_out"] is False
    finally:
        del ALLOWLIST["_test_echo"]


@pytest.mark.asyncio
async def test_env_strips_secret_shaped_variables(
    workspace: Path, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "sk-should-not-leak")
    ALLOWLIST["_test_env"] = [
        sys.executable,
        "-c",
        "import os; print('KEY_PRESENT' if 'MODEL_API_KEY' in os.environ else 'KEY_ABSENT')",
    ]
    try:
        tool_context = _tool_context(workspace, tmp_path / "run")
        result = await run_allowlisted_command(tool_context, "_test_env")
        assert "KEY_ABSENT" in result["stdout"]
    finally:
        del ALLOWLIST["_test_env"]


@pytest.mark.asyncio
async def test_timeout_is_captured_not_raised(workspace: Path, tmp_path: Path, monkeypatch) -> None:
    import agentic_builder.tools.subprocess_runner as mod

    monkeypatch.setattr(mod, "_DEFAULT_TIMEOUT_SECONDS", 0.01)
    ALLOWLIST["_test_sleep"] = [sys.executable, "-c", "import time; time.sleep(2)"]
    try:
        tool_context = _tool_context(workspace, tmp_path / "run")
        result = await run_allowlisted_command(tool_context, "_test_sleep")
        assert result["timed_out"] is True
        assert result["returncode"] is None
    finally:
        del ALLOWLIST["_test_sleep"]


@pytest.mark.asyncio
async def test_command_events_are_logged(workspace: Path, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    ALLOWLIST["_test_echo2"] = [sys.executable, "-c", "print('x')"]
    try:
        tool_context = _tool_context(workspace, run_dir)
        await run_allowlisted_command(tool_context, "_test_echo2")
        events_path = run_dir / "events.jsonl"
        assert events_path.exists()
        lines = events_path.read_text("utf-8").splitlines()
        assert any(json.loads(line)["type"] == "command_executed" for line in lines)
    finally:
        del ALLOWLIST["_test_echo2"]

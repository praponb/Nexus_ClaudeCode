"""Allowlisted subprocess execution for agent-triggered build/test/lint commands.

Security constraints from the spec: never execute shell commands copied
from requirement files without validation and an allowlisted execution
policy; restrict subprocesses with timeouts, safe working directories,
captured output, and explicit command construction (``shell=False``,
argv built from a fixed template -- never a raw string from any source).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from agentic_builder.errors import CommandNotAllowlistedError
from agentic_builder.events import append_event
from agentic_builder.tools.workspace import resolve_within

#: Fixed argv templates. Never derived from requirement-file or model text --
#: only the ``command_key`` (validated against this dict) selects one.
ALLOWLIST: dict[str, list[str]] = {
    "npm_install": ["npm", "install"],
    "npm_run_build": ["npm", "run", "build"],
    "npm_run_lint": ["npm", "run", "lint"],
    "npm_run_typecheck": ["npm", "run", "typecheck"],
    "npm_test": ["npm", "test", "--", "--watchAll=false"],
    "pytest": [sys.executable, "-m", "pytest"],
    "ruff_check": [sys.executable, "-m", "ruff", "check", "."],
    "ruff_format_check": [sys.executable, "-m", "ruff", "format", "--check", "."],
    "mypy": [sys.executable, "-m", "mypy", "."],
    "pip_install_dev": [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
    "alembic_upgrade_head": ["alembic", "upgrade", "head"],
    "uvicorn_smoke_import": [sys.executable, "-c", "import app.main"],
}

_SAFE_EXTRA_ARG = re.compile(r"^[A-Za-z0-9_.\-=/:]+$")
_DEFAULT_TIMEOUT_SECONDS = 180
_SECRET_ENV_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD")


def _minimal_env() -> dict[str, str]:
    """A copy of the current environment with anything secret-shaped stripped."""
    return {
        key: value
        for key, value in os.environ.items()
        if not any(key.upper().endswith(suffix) for suffix in _SECRET_ENV_SUFFIXES)
    }


def _sanitize_extra_args(extra_args: list[str]) -> list[str]:
    for arg in extra_args:
        if not _SAFE_EXTRA_ARG.match(arg):
            raise CommandNotAllowlistedError(
                f"Extra argument {arg!r} contains disallowed characters."
            )
    return extra_args


async def run_allowlisted_command(
    tool_context: Any,
    command_key: str,
    extra_args_json: str = "[]",
    cwd_relative: str = ".",
) -> dict[str, Any]:
    """Run a pre-approved build/test/lint command and capture its output.

    Args:
      command_key: One of the fixed allowlisted command names (e.g.
        ``"npm_test"``, ``"pytest"``, ``"ruff_check"``). Arbitrary shell
        strings are never accepted here.
      extra_args_json: JSON array of additional argv tokens, restricted to
        safe characters (no shell metacharacters).
      cwd_relative: Working directory relative to the workspace root.
    """
    import json

    if command_key not in ALLOWLIST:
        raise CommandNotAllowlistedError(
            f"{command_key!r} is not on the command allowlist: {sorted(ALLOWLIST)}"
        )

    try:
        extra_args = json.loads(extra_args_json)
    except json.JSONDecodeError as exc:
        return {"error": f"extra_args_json is not valid JSON: {exc}"}
    if not isinstance(extra_args, list) or not all(isinstance(a, str) for a in extra_args):
        return {"error": "extra_args_json must decode to an array of strings"}
    extra_args = _sanitize_extra_args(extra_args)

    workspace = Path(tool_context.state["workspace"])
    run_dir = Path(tool_context.state["run_dir"])
    cycle = int(tool_context.state["cycle"])
    dry_run = bool(tool_context.state.get("dry_run", False))
    cwd = resolve_within(workspace, cwd_relative)

    argv = [*ALLOWLIST[command_key], *extra_args]

    if dry_run:
        append_event(
            run_dir,
            {"type": "would_run_command", "cycle": cycle, "command_key": command_key, "argv": argv},
        )
        return {"dry_run": True, "argv": argv}

    cwd.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(  # noqa: S603 -- argv is a fixed allowlisted template, shell=False
            argv,
            cwd=str(cwd),
            env=_minimal_env(),
            capture_output=True,
            text=True,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
            shell=False,
            check=False,
        )
        outcome: dict[str, Any] = {
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout[-8000:],
            "stderr": result.stderr[-8000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        outcome = {
            "argv": argv,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "timed_out": True,
        }

    append_event(
        run_dir,
        {
            "type": "command_executed",
            "cycle": cycle,
            "command_key": command_key,
            "argv": argv,
            "returncode": outcome["returncode"],
            "timed_out": outcome["timed_out"],
        },
    )
    return outcome

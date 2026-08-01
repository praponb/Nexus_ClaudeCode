"""Append-only, secret-masked event logging shared by the orchestrator and tools.

Kept as its own module (rather than living in ``state.py`` or ``tools/``) so
both can import it without a circular dependency.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from agentic_builder.config import Settings, mask_secrets


def _mask_deep(value: Any, settings: Settings | None) -> Any:
    if isinstance(value, str):
        return mask_secrets(value, settings)
    if isinstance(value, dict):
        return {k: _mask_deep(v, settings) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_deep(v, settings) for v in value]
    return value


def append_event(
    run_dir: Path,
    event: dict[str, Any],
    settings: Settings | None = None,
) -> None:
    """Append one secret-masked JSON event to ``<run_dir>/events.jsonl``.

    Uses an append + fsync rather than the atomic-replace pattern used for
    whole-file writes, since events.jsonl is written incrementally by many
    calls over the lifetime of a run.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": time.time(), **_mask_deep(event, settings)}
    path = run_dir / "events.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True))

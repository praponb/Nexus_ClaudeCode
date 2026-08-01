"""Read-only access to files already inside the workspace.

Used by all four agents to read prior-cycle summaries, the current
detailed design specification, and each other's generated output. Writes
go through ``tools/owned_writers.py`` instead, which enforces per-agent
ownership boundaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic_builder.tools.workspace import resolve_within, wrap_untrusted


async def read_workspace_file(tool_context: Any, relative_path: str) -> dict[str, Any]:
    """Read a file already present in the workspace, e.g. ``frontend/src/App.tsx``
    or ``detail-design-specification.md``.

    Confined to the workspace root; returns wrapped/delimited content since
    prior agent output (including from earlier cycles) is still untrusted
    with respect to instruction-following.
    """
    workspace = Path(tool_context.state["workspace"])
    path = resolve_within(workspace, relative_path)
    if not path.is_file():
        return {"error": f"No such workspace file: {relative_path!r}"}
    return {"relative_path": relative_path, "content": wrap_untrusted(path.read_text("utf-8"))}

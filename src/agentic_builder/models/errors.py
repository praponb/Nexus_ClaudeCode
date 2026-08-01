from __future__ import annotations

from agentic_builder.errors import AgenticBuilderError


class ModelResolutionError(AgenticBuilderError):
    """The configured model/provider rejected the request (bad id, auth, etc.).

    Raised instead of silently retrying against a different model.
    """

"""Shared exception types for the orchestrator.

Kept separate from ``models/errors.py`` (which is model-adapter specific)
so tools and the orchestrator can raise/catch without importing the model
layer.
"""

from __future__ import annotations


class AgenticBuilderError(Exception):
    """Base class for all orchestrator-raised errors."""


class ConfigError(AgenticBuilderError):
    """Configuration is missing or invalid."""


class PathTraversalError(AgenticBuilderError):
    """A tool attempted to read or write outside its allowed root."""


class OwnershipViolationError(AgenticBuilderError):
    """A tool attempted to write outside the calling agent's owned subtree."""


class InputValidationError(AgenticBuilderError):
    """Required requirement Markdown files are missing or unreadable."""


class FatalOrchestrationError(AgenticBuilderError):
    """A setup-level failure that must abort the run (not a QA test failure)."""

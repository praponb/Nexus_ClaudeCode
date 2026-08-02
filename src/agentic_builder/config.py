"""Externalized, validated configuration for the orchestrator.

All model-provider and workspace settings come from environment variables
(optionally loaded from a ``.env`` file) so that no credentials or
environment-specific paths are ever hard-coded. See the repo-root ``.env``
(and README.md) for the full list of supported variables.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentic_builder.errors import ConfigError

#: Env vars/values that must never appear verbatim in logs, events, or reports.
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization:\s*bearer)\s*[:=]?\s*"
    r"([A-Za-z0-9\-_.]{8,})"
)
_MASK = "***REDACTED***"


class ModelProvider(str, Enum):
    """How ``MODEL_NAME`` should be resolved into a callable model."""

    MOONSHOT = "moonshot"
    """Route through litellm's built-in Moonshot AI provider."""

    LITELLM = "litellm"
    """Pass MODEL_NAME to litellm verbatim (any other provider/model string)."""

    FAKE = "fake"
    """No network calls; use the deterministic in-process test double."""


class Settings(BaseSettings):
    """Orchestrator configuration, loaded from the environment / ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    MODEL_PROVIDER: ModelProvider = ModelProvider.MOONSHOT
    MODEL_NAME: str = "kimi-k3"
    MODEL_API_BASE: str | None = None
    MODEL_API_KEY: SecretStr | None = None
    MODEL_REASONING_EFFORT: str | None = None

    input_dir: Path = Field(default=Path("requirements"), alias="AGENTIC_BUILDER_INPUT_DIR")
    workspace: Path = Field(default=Path("."), alias="AGENTIC_BUILDER_WORKSPACE")
    cycles: int = Field(default=3, alias="AGENTIC_BUILDER_CYCLES")
    log_level: str = Field(default="INFO", alias="AGENTIC_BUILDER_LOG_LEVEL")
    agent_timeout_seconds: float = Field(
        default=2400.0, alias="AGENTIC_BUILDER_AGENT_TIMEOUT_SECONDS"
    )

    # Set by the CLI, not read from the environment.
    dry_run: bool = False
    verbose: bool = False

    @field_validator("MODEL_REASONING_EFFORT")
    @classmethod
    def _validate_reasoning_effort(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if value not in {"low", "high", "max"}:
            raise ValueError("MODEL_REASONING_EFFORT must be one of: low, high, max")
        return value


def validate_model_config(settings: Settings) -> None:
    """Fail fast with an actionable message if the model can't be reached.

    This is a missing-credential check, not a suspect-model check: kimi-k3
    is a confirmed real Moonshot AI model id (see ASSUMPTIONS.md), so the
    failure mode we guard against here is "no API key configured", not "the
    model name looks wrong". A genuinely bad model id/typo is still caught
    at call time in ``models/provider.py`` and surfaced as
    ``ModelResolutionError`` rather than silently retried against a
    different model.
    """
    if settings.MODEL_PROVIDER is ModelProvider.FAKE:
        return

    if not settings.MODEL_NAME.strip():
        raise ConfigError("MODEL_NAME must not be empty.")

    if settings.MODEL_API_KEY is None or not settings.MODEL_API_KEY.get_secret_value().strip():
        raise ConfigError(
            "MODEL_API_KEY is not configured. "
            f"MODEL_PROVIDER={settings.MODEL_PROVIDER.value!r} requires an API key. "
            "For the default MODEL_PROVIDER=moonshot / MODEL_NAME=kimi-k3, create one "
            "at https://platform.kimi.ai/console/api-keys (requires an account with "
            "at least a $1 top-up) and set MODEL_API_KEY in your .env file. "
            "See README.md for full setup steps."
        )


def mask_secrets(text: str, settings: Settings | None = None) -> str:
    """Redact known secret values and secret-shaped substrings from ``text``.

    Used everywhere text might be persisted or printed (logs, events.jsonl,
    reports, exception messages) so credentials never leak, even if a tool
    or model response happens to echo them back.
    """
    if settings is not None and settings.MODEL_API_KEY is not None:
        key = settings.MODEL_API_KEY.get_secret_value()
        if key:
            text = text.replace(key, _MASK)
    return _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}={_MASK}", text)

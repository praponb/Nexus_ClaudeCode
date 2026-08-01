"""Shared LlmAgent construction: uniform retries, timeouts, and prompt loading."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from importlib import resources
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm
from google.adk.workflow import RetryConfig

#: Bounded exponential backoff for transient model failures, applied
#: uniformly to all four agents (spec: "Add retries with bounded exponential
#: backoff for transient model failures").
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=20.0,
    backoff_factor=2.0,
)

#: Per-turn timeout in seconds (spec: "Add timeouts and clear failure handling").
DEFAULT_AGENT_TIMEOUT_SECONDS = 300.0

ToolFunc = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


def _load_prompt(filename: str) -> str:
    return resources.files("agentic_builder.prompts").joinpath(filename).read_text(encoding="utf-8")


def build_llm_agent(
    *,
    role: str,
    model: BaseLlm,
    tools: list[Any],
    output_key: str,
    prompt_filename: str,
    description: str,
) -> LlmAgent:
    """Build an LlmAgent for ``role`` with uniform retry/timeout policy.

    The agent's instruction is loaded verbatim from ``prompts/<prompt_filename>``
    -- fixed text we author, never touched by requirement-file content. See
    that prompt file for the agent's full responsibilities and the
    prompt-injection defense clause.
    """
    return LlmAgent(
        name=role,
        description=description,
        model=model,
        instruction=_load_prompt(prompt_filename),
        tools=tools,
        output_key=output_key,
        retry_config=DEFAULT_RETRY_CONFIG,
        timeout=DEFAULT_AGENT_TIMEOUT_SECONDS,
    )

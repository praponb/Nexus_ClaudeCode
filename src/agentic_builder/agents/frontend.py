from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm

from agentic_builder.agents.base import DEFAULT_AGENT_TIMEOUT_SECONDS, build_llm_agent
from agentic_builder.tools.file_io import read_workspace_file
from agentic_builder.tools.owned_writers import make_files_writer
from agentic_builder.tools.subprocess_runner import run_allowlisted_command


def build_frontend_agent(
    model: BaseLlm, timeout: float = DEFAULT_AGENT_TIMEOUT_SECONDS
) -> LlmAgent:
    return build_llm_agent(
        role="frontend",
        model=model,
        tools=[
            read_workspace_file,
            make_files_writer("frontend", ("frontend",), "frontend-summary.md"),
            run_allowlisted_command,
        ],
        output_key="frontend_result",
        prompt_filename="frontend.md",
        description="Owns frontend/; implements UI matching layout.md and the frontend stack.",
        timeout=timeout,
    )

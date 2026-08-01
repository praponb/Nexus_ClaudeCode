from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm

from agentic_builder.agents.base import build_llm_agent
from agentic_builder.tools.file_io import read_workspace_file
from agentic_builder.tools.owned_writers import make_files_writer
from agentic_builder.tools.subprocess_runner import run_allowlisted_command


def build_backend_agent(model: BaseLlm) -> LlmAgent:
    return build_llm_agent(
        role="backend",
        model=model,
        tools=[
            read_workspace_file,
            make_files_writer("backend", ("backend", "scripts"), "backend-summary.md"),
            run_allowlisted_command,
        ],
        output_key="backend_result",
        prompt_filename="backend.md",
        description="Owns backend/ and scripts/; implements APIs, persistence, and security.",
    )

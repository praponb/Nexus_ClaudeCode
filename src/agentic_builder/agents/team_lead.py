from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm

from agentic_builder.agents.base import build_llm_agent
from agentic_builder.tools.file_io import read_workspace_file
from agentic_builder.tools.markdown_discovery import discover_markdown_files, read_markdown_file
from agentic_builder.tools.owned_writers import make_design_writer


def build_team_lead_agent(model: BaseLlm) -> LlmAgent:
    return build_llm_agent(
        role="team_lead",
        model=model,
        tools=[
            discover_markdown_files,
            read_markdown_file,
            read_workspace_file,
            make_design_writer(),
        ],
        output_key="team_lead_result",
        prompt_filename="team_lead.md",
        description="Owns detail-design-specification.md and cycle plans; reviews QA/impl output.",
    )

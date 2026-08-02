from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm

from agentic_builder.agents.base import DEFAULT_AGENT_TIMEOUT_SECONDS, build_llm_agent
from agentic_builder.tools.file_io import read_workspace_file
from agentic_builder.tools.owned_writers import make_files_writer, make_qa_execution_writer
from agentic_builder.tools.subprocess_runner import run_allowlisted_command


def build_qa_agent(model: BaseLlm, timeout: float = DEFAULT_AGENT_TIMEOUT_SECONDS) -> LlmAgent:
    return build_llm_agent(
        role="qa",
        model=model,
        tools=[
            read_workspace_file,
            make_files_writer(
                "qa", ("testcase",), "qa-test-design-summary.md", tool_name="write_testcase_files"
            ),
            make_qa_execution_writer(),
            run_allowlisted_command,
        ],
        output_key="qa_result",
        prompt_filename="qa.md",
        description="Owns testcase/; designs and executes tests, reports honest pass/fail/blocked.",
        timeout=timeout,
    )

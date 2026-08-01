"""The four agents: Team Lead, Frontend Developer, Backend Developer, QA Tester."""

from agentic_builder.agents.backend import build_backend_agent
from agentic_builder.agents.frontend import build_frontend_agent
from agentic_builder.agents.qa import build_qa_agent
from agentic_builder.agents.team_lead import build_team_lead_agent

__all__ = [
    "build_backend_agent",
    "build_frontend_agent",
    "build_qa_agent",
    "build_team_lead_agent",
]

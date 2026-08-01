"""Requirement traceability records, populated from the Team Lead's structured
tool arguments (never scraped from free-text Markdown)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RequirementRecord(BaseModel):
    req_id: str
    description: str
    source_file: str
    status: str = "proposed"
    """e.g. proposed, designed, implemented, tested, blocked."""
    design_ref: str | None = None
    implementing_files: list[str] = Field(default_factory=list)
    test_ids: list[str] = Field(default_factory=list)
    last_cycle_updated: int = 0


class TraceabilityMatrix(BaseModel):
    requirements: dict[str, RequirementRecord] = Field(default_factory=dict)

    def to_markdown_table(self) -> str:
        header = (
            "| Req ID | Description | Status | Design Ref | Implementing Files | "
            "Test IDs | Last Cycle |\n"
            "|---|---|---|---|---|---|---|\n"
        )
        rows = []
        for req_id in sorted(self.requirements):
            r = self.requirements[req_id]
            rows.append(
                f"| {r.req_id} | {r.description} | {r.status} | {r.design_ref or ''} | "
                f"{', '.join(r.implementing_files)} | {', '.join(r.test_ids)} | "
                f"{r.last_cycle_updated} |"
            )
        return header + "\n".join(rows)

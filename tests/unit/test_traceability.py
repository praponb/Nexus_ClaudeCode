from __future__ import annotations

from agentic_builder.schemas.traceability import RequirementRecord, TraceabilityMatrix


def test_to_markdown_table_includes_all_requirements_sorted() -> None:
    matrix = TraceabilityMatrix(
        requirements={
            "REQ-2": RequirementRecord(
                req_id="REQ-2",
                description="second",
                source_file="specification.md",
                status="designed",
            ),
            "REQ-1": RequirementRecord(
                req_id="REQ-1",
                description="first",
                source_file="specification.md",
                status="implemented",
                implementing_files=["frontend/App.tsx"],
                test_ids=["TC-1-001"],
                last_cycle_updated=2,
            ),
        }
    )
    table = matrix.to_markdown_table()
    lines = table.splitlines()
    assert lines[0].startswith("| Req ID")
    req1_line_index = next(i for i, line in enumerate(lines) if line.startswith("| REQ-1"))
    req2_line_index = next(i for i, line in enumerate(lines) if line.startswith("| REQ-2"))
    assert req1_line_index < req2_line_index  # sorted by req_id
    assert "frontend/App.tsx" in lines[req1_line_index]
    assert "TC-1-001" in lines[req1_line_index]


def test_empty_matrix_produces_header_only() -> None:
    matrix = TraceabilityMatrix()
    table = matrix.to_markdown_table()
    assert table.strip().splitlines()[0].startswith("| Req ID")

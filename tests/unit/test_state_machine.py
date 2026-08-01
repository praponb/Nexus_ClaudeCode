from __future__ import annotations

from pathlib import Path

from agentic_builder.state import (
    RunState,
    RunStateDoc,
    cycle_implement_state,
    cycle_review_state,
    load_state,
    save_state,
    state_sequence,
)


def test_state_sequence_has_exactly_three_cycles_worth_of_states() -> None:
    seq = state_sequence(3)
    assert seq[0] == "INITIALIZE"
    assert seq[1] == "ANALYZE_INPUTS"
    assert seq[2] == "TEAM_LEAD_DESIGN"
    assert seq[-3] == "TEAM_LEAD_FINAL_REVIEW"
    assert seq[-2] == "FINAL_VALIDATION"
    assert seq[-1] == "COMPLETE"
    cycle_states = [s for s in seq if s.startswith("CYCLE_")]
    review_states = [s for s in seq if s.startswith("TEAM_LEAD_REVIEW_")]
    assert cycle_states == [
        "CYCLE_1_IMPLEMENT_AND_TEST",
        "CYCLE_2_IMPLEMENT_AND_TEST",
        "CYCLE_3_IMPLEMENT_AND_TEST",
    ]
    assert review_states == ["TEAM_LEAD_REVIEW_1", "TEAM_LEAD_REVIEW_2", "TEAM_LEAD_REVIEW_3"]


def test_state_sequence_scales_with_cycles_total() -> None:
    seq = state_sequence(1)
    assert [s for s in seq if s.startswith("CYCLE_")] == ["CYCLE_1_IMPLEMENT_AND_TEST"]


def test_cycle_state_name_helpers() -> None:
    assert cycle_implement_state(2) == "CYCLE_2_IMPLEMENT_AND_TEST"
    assert cycle_review_state(2) == "TEAM_LEAD_REVIEW_2"


def test_run_state_doc_mark_done_and_is_done() -> None:
    doc = RunStateDoc.new(
        cycles_total=3, workspace="/ws", input_dir="/in", input_manifest_hash="abc"
    )
    assert not doc.is_done(RunState.INITIALIZE.value)
    doc.mark_done(RunState.INITIALIZE.value)
    assert doc.is_done(RunState.INITIALIZE.value)
    assert doc.current_state == RunState.INITIALIZE.value


def test_run_state_doc_mark_failed() -> None:
    doc = RunStateDoc.new(
        cycles_total=3, workspace="/ws", input_dir="/in", input_manifest_hash="abc"
    )
    doc.mark_failed("CYCLE_2_IMPLEMENT_AND_TEST", "boom")
    assert doc.current_state == RunState.FAILED.value
    assert doc.error == "boom"
    assert doc.history[-1]["status"] == "failed"


def test_save_and_load_state_roundtrip(tmp_path: Path) -> None:
    doc = RunStateDoc.new(
        cycles_total=3, workspace="/ws", input_dir="/in", input_manifest_hash="abc"
    )
    doc.mark_done(RunState.INITIALIZE.value)
    save_state(tmp_path, doc)
    loaded = load_state(tmp_path)
    assert loaded.run_id == doc.run_id
    assert loaded.is_done(RunState.INITIALIZE.value)
    assert loaded.cycles_total == 3

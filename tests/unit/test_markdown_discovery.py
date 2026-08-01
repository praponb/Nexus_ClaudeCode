from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agentic_builder.errors import InputValidationError
from agentic_builder.tools.markdown_discovery import (
    discover_markdown_files,
    load_and_validate_inputs,
    read_markdown_file,
)


def test_load_and_validate_inputs_succeeds_for_valid_fixture(fixtures_dir: Path) -> None:
    manifest = load_and_validate_inputs(fixtures_dir / "requirements_valid")
    names = {f.relative_path for f in manifest.files}
    assert {"specification.md", "layout.md", "front-back-end-stack.md"} <= names
    assert manifest.missing_required == []


def test_load_and_validate_inputs_raises_for_missing_required(fixtures_dir: Path) -> None:
    with pytest.raises(InputValidationError, match="layout.md"):
        load_and_validate_inputs(fixtures_dir / "requirements_missing_required")


def test_load_and_validate_inputs_raises_for_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError):
        load_and_validate_inputs(tmp_path / "does-not-exist")


def test_additional_markdown_files_are_discovered(tmp_path: Path) -> None:
    for name in ("specification.md", "layout.md", "front-back-end-stack.md", "extra-notes.md"):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    manifest = load_and_validate_inputs(tmp_path)
    names = {f.relative_path for f in manifest.files}
    assert "extra-notes.md" in names
    extra = next(f for f in manifest.files if f.relative_path == "extra-notes.md")
    assert extra.required is False


def test_combined_hash_is_stable_and_changes_with_content(tmp_path: Path) -> None:
    for name in ("specification.md", "layout.md", "front-back-end-stack.md"):
        (tmp_path / name).write_text("v1", encoding="utf-8")
    manifest1 = load_and_validate_inputs(tmp_path)
    manifest2 = load_and_validate_inputs(tmp_path)
    assert manifest1.combined_hash == manifest2.combined_hash

    (tmp_path / "specification.md").write_text("v2", encoding="utf-8")
    manifest3 = load_and_validate_inputs(tmp_path)
    assert manifest3.combined_hash != manifest1.combined_hash


@pytest.mark.asyncio
async def test_discover_markdown_files_tool(fixtures_dir: Path) -> None:
    tool_context = SimpleNamespace(state={"input_dir": str(fixtures_dir / "requirements_valid")})
    result = await discover_markdown_files(tool_context)
    names = {f["relative_path"] for f in result["files"]}
    assert "specification.md" in names


@pytest.mark.asyncio
async def test_read_markdown_file_wraps_content_as_untrusted(fixtures_dir: Path) -> None:
    tool_context = SimpleNamespace(state={"input_dir": str(fixtures_dir / "requirements_valid")})
    result = await read_markdown_file(tool_context, "specification.md")
    assert "BEGIN UNTRUSTED DATA" in result["content"]
    assert "Team Task Tracker" in result["content"]


@pytest.mark.asyncio
async def test_read_markdown_file_confined_to_input_dir(fixtures_dir: Path) -> None:
    tool_context = SimpleNamespace(state={"input_dir": str(fixtures_dir / "requirements_valid")})
    from agentic_builder.errors import PathTraversalError

    with pytest.raises(PathTraversalError):
        await read_markdown_file(tool_context, "../requirements_missing_required/specification.md")

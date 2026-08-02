from __future__ import annotations

from pathlib import Path

import pytest

from agentic_builder.cli import main


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "agentic-builder" in out


def test_validate_reports_missing_required_files(
    fixtures_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        ["validate", "--input-dir", str(fixtures_dir / "requirements_missing_required")]
    )
    assert exit_code == 1


def test_validate_reports_missing_api_key(
    fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force-empty rather than delenv: env vars take precedence over a real
    # .env file that may exist in the repo root for actual usage, so
    # deleting the process env var alone wouldn't stop Settings from
    # falling back to a real key configured there.
    monkeypatch.setenv("MODEL_API_KEY", "")
    exit_code = main(["validate", "--input-dir", str(fixtures_dir / "requirements_valid")])
    assert exit_code == 1


def test_run_rejects_non_default_cycles_without_dev_cycles(
    fixtures_dir: Path, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "fake")
    exit_code = main(
        [
            "run",
            "--input-dir",
            str(fixtures_dir / "requirements_valid"),
            "--workspace",
            str(workspace),
            "--cycles",
            "1",
        ]
    )
    assert exit_code == 2
    assert not (workspace / "runs").exists()


def test_run_with_fake_model_completes_and_report_reads_it_back(
    fixtures_dir: Path,
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "fake")
    exit_code = main(
        [
            "run",
            "--input-dir",
            str(fixtures_dir / "requirements_valid"),
            "--workspace",
            str(workspace),
        ]
    )
    assert exit_code == 0

    run_dirs = list((workspace / "runs").iterdir())
    assert len(run_dirs) == 1
    run_id = run_dirs[0].name

    capsys.readouterr()  # clear captured output from the run above
    exit_code = main(["report", "--run-id", run_id, "--workspace", str(workspace)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "# Final Quality Report" in out


def test_dry_run_command_leaves_generated_dirs_empty(
    fixtures_dir: Path, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "fake")
    exit_code = main(
        [
            "dry-run",
            "--input-dir",
            str(fixtures_dir / "requirements_valid"),
            "--workspace",
            str(workspace),
        ]
    )
    assert exit_code == 0
    assert list((workspace / "frontend").iterdir()) == []

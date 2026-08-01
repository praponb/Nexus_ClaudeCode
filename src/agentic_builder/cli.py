"""Command-line interface.

agentic-builder run --input-dir ./requirements --workspace . --cycles 3 --verbose
agentic-builder validate --input-dir ./requirements
agentic-builder resume --run-id <id> --workspace .
agentic-builder dry-run --input-dir ./requirements --workspace .
agentic-builder test [pytest-args...]
agentic-builder report --run-id <id> --workspace .
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from agentic_builder.config import ConfigError, Settings, mask_secrets, validate_model_config
from agentic_builder.errors import FatalOrchestrationError, InputValidationError
from agentic_builder.logging import configure_logging, get_logger
from agentic_builder.orchestrator import Orchestrator
from agentic_builder.tools.markdown_discovery import load_and_validate_inputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-builder",
        description=(
            "Four-agent Google ADK orchestrator: turns Markdown requirements into a "
            "generated full-stack web app over three design/implement/QA cycles."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--input-dir", default=None, help="Directory containing requirement *.md files."
        )
        p.add_argument(
            "--workspace", default=None, help="Root directory for generated output and runs/."
        )
        p.add_argument(
            "--verbose", action="store_true", help="Print detailed events and tool activity."
        )

    run_p = sub.add_parser("run", help="Start a new run (production default: exactly 3 cycles).")
    add_common(run_p)
    run_p.add_argument(
        "--cycles", type=int, default=3, help="Number of cycles (production default: 3)."
    )
    run_p.add_argument(
        "--dev-cycles",
        action="store_true",
        help="Allow --cycles to differ from 3. Development/testing only.",
    )
    run_p.add_argument(
        "--dry-run", action="store_true", help="Inspect plans without writing generated app files."
    )

    dry_p = sub.add_parser("dry-run", help="Sugar for `run --dry-run`.")
    add_common(dry_p)
    dry_p.add_argument("--cycles", type=int, default=3)
    dry_p.add_argument("--dev-cycles", action="store_true")

    resume_p = sub.add_parser("resume", help="Resume an interrupted run.")
    add_common(resume_p)
    resume_p.add_argument("--run-id", required=True)

    validate_p = sub.add_parser("validate", help="Validate input files and configuration.")
    add_common(validate_p)

    test_p = sub.add_parser("test", help="Run the orchestrator's own test suite (pytest).")
    test_p.add_argument("pytest_args", nargs=argparse.REMAINDER)

    report_p = sub.add_parser("report", help="Print or export the final run summary.")
    add_common(report_p)
    report_p.add_argument("--run-id", required=True)
    report_p.add_argument("--format", choices=["md", "json"], default="md")
    report_p.add_argument(
        "--out", default=None, help="Write the report to this path instead of stdout."
    )

    return parser


def _settings_from_args(args: argparse.Namespace) -> Settings:
    kwargs: dict[str, object] = {"verbose": getattr(args, "verbose", False)}
    if getattr(args, "input_dir", None):
        kwargs["input_dir"] = Path(args.input_dir)
    if getattr(args, "workspace", None):
        kwargs["workspace"] = Path(args.workspace)
    if hasattr(args, "cycles"):
        kwargs["cycles"] = args.cycles
    if hasattr(args, "dry_run"):
        kwargs["dry_run"] = args.dry_run
    return Settings(**kwargs)  # type: ignore[arg-type]


def _cmd_validate(args: argparse.Namespace) -> int:
    logger = get_logger()
    settings = _settings_from_args(args)
    try:
        manifest = load_and_validate_inputs(settings.input_dir)
    except InputValidationError as exc:
        logger.error(str(exc))
        return 1
    logger.info(
        f"Input directory OK: {settings.input_dir} ({len(manifest.files)} markdown file(s))."
    )
    try:
        validate_model_config(settings)
    except ConfigError as exc:
        logger.error(str(exc))
        return 1
    logger.info(
        f"Model configuration OK: provider={settings.MODEL_PROVIDER.value} "
        f"model={settings.MODEL_NAME}."
    )
    return 0


def _cmd_run(args: argparse.Namespace, *, force_dry_run: bool = False) -> int:
    logger = get_logger()
    settings = _settings_from_args(args)
    if force_dry_run:
        settings.dry_run = True

    if settings.cycles != 3 and not getattr(args, "dev_cycles", False):
        logger.error(
            "Refusing to run with --cycles="
            f"{settings.cycles} without --dev-cycles. The production workflow enforces "
            "exactly three cycles; pass --dev-cycles to explicitly opt into a different "
            "count for development or testing."
        )
        return 2

    orchestrator = Orchestrator(settings)
    try:
        asyncio.run(orchestrator.run(resume=False))
    except FatalOrchestrationError as exc:
        logger.error(f"Run failed: {mask_secrets(str(exc), settings)}")
        return 1
    logger.info(f"Run complete: {orchestrator.run_id}")
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    logger = get_logger()
    settings = _settings_from_args(args)
    orchestrator = Orchestrator(settings, run_id=args.run_id)
    try:
        asyncio.run(orchestrator.run(resume=True))
    except FatalOrchestrationError as exc:
        logger.error(f"Resume failed: {mask_secrets(str(exc), settings)}")
        return 1
    logger.info(f"Resume complete: {orchestrator.run_id}")
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    return subprocess.call([sys.executable, "-m", "pytest", *args.pytest_args])


def _cmd_report(args: argparse.Namespace) -> int:
    logger = get_logger()
    settings = _settings_from_args(args)
    run_dir = Path(settings.workspace).resolve() / "runs" / args.run_id
    report_path = run_dir / "final-report.md"
    if not report_path.exists():
        logger.error(f"No final report found for run {args.run_id!r} at {report_path}")
        return 1
    content = report_path.read_text("utf-8")
    output = (
        json.dumps({"run_id": args.run_id, "report_markdown": content})
        if args.format == "json"
        else content
    )
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(getattr(args, "verbose", False))

    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "dry-run":
        return _cmd_run(args, force_dry_run=True)
    if args.command == "resume":
        return _cmd_resume(args)
    if args.command == "test":
        return _cmd_test(args)
    if args.command == "report":
        return _cmd_report(args)

    parser.error(f"Unknown command: {args.command}")
    return 2  # pragma: no cover -- parser.error exits the process

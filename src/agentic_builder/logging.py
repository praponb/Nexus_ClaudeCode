"""Structured, agent-labelled terminal logging.

Concise by default; ``--verbose`` adds tool args/results (secret-masked),
retry attempts, and command argv/exit codes. Both levels are driven by the
same event shape the orchestrator also persists to ``events.jsonl``, so
terminal output and the durable event log never disagree.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from agentic_builder.config import Settings, mask_secrets

_LOGGER_NAME = "agentic_builder"


def configure_logging(verbose: bool) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def log_event(
    event: dict[str, Any],
    *,
    verbose: bool,
    settings: Settings | None = None,
) -> None:
    """Render one orchestrator event as a terminal log line.

    Concise default line: ``STATE=... cycle=... agent=... status=...``.
    Verbose adds every other event field (masked).
    """
    logger = get_logger()
    event_type = event.get("type", "event")
    state = event.get("state", "-")
    cycle = event.get("cycle", "-")
    agent = event.get("owner") or event.get("role") or "-"
    status = event.get("status") or event_type

    line = f"type={event_type} state={state} cycle={cycle} agent={agent} status={status}"
    if verbose:
        extras = {
            k: v
            for k, v in event.items()
            if k not in {"type", "state", "cycle", "owner", "role", "status", "timestamp"}
        }
        if extras:
            line += " " + mask_secrets(str(extras), settings)
    logger.info(line)

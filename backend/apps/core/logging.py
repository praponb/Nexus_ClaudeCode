"""Structured JSON logging with correlation ID (NFR-011).

Never log credentials, tokens, session IDs, or financial values here.
"""

import json
import logging
import time

from apps.core.context import correlation_id_var


class JsonFormatter(logging.Formatter):
    converter = time.gmtime  # type: ignore[assignment]  # stdlib typeshed quirk

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + "Z",
            "level": record.levelname.lower(),
            "service": "backend",
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)

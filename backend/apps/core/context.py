"""Request-scoped context (correlation ID) shared by logging, errors and audit."""

from contextvars import ContextVar

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

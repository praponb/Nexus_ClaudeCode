# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml uv.lock README.md ./
COPY manage.py ./
COPY config ./config
COPY apps ./apps

RUN uv sync --frozen --no-dev && chown -R appuser:appuser /app

EXPOSE 8000

FROM base AS dev
RUN uv sync --frozen
USER appuser
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS production
USER appuser
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

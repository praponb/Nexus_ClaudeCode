# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md ./
COPY manage.py ./
COPY config ./config
COPY apps ./apps

RUN pip install --no-cache-dir . && chown appuser:appuser /app

EXPOSE 8000

FROM base AS dev
RUN pip install --no-cache-dir ".[dev]"
USER appuser
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS production
USER appuser
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

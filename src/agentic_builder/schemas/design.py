"""Detailed design specification revision-history entries."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field


class DesignRevision(BaseModel):
    cycle: int
    summary: str
    changes: list[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)

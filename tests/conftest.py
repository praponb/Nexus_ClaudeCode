from __future__ import annotations

from pathlib import Path

import pytest

from agentic_builder.config import ModelProvider, Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


def fake_settings(**overrides: object) -> Settings:
    """Build Settings pointed at the fake model, with sensible test defaults."""
    kwargs: dict[str, object] = {
        "MODEL_PROVIDER": ModelProvider.FAKE,
        "input_dir": FIXTURES_DIR / "requirements_valid",
        "cycles": 3,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)  # type: ignore[arg-type]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws

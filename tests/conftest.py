from __future__ import annotations

from pathlib import Path

import pytest

from agentic_builder.config import ModelProvider, Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


#: Every env var Settings reads. Pydantic's ``_env_file=None`` only disables the
#: dotenv file -- it does NOT stop BaseSettings from reading ``os.environ`` -- so
#: without this the suite inherits whatever the developer's shell exports and
#: tests asserting default/missing-credential behaviour fail. Notably CLAUDE.md
#: documents running the suite as ``MODEL_PROVIDER=fake pytest``, which is
#: exactly what used to break it.
_SETTINGS_ENV_VARS = (
    "MODEL_PROVIDER",
    "MODEL_NAME",
    "MODEL_API_BASE",
    "MODEL_API_KEY",
    "MODEL_REASONING_EFFORT",
    "AGENTIC_BUILDER_INPUT_DIR",
    "AGENTIC_BUILDER_WORKSPACE",
    "AGENTIC_BUILDER_CYCLES",
    "AGENTIC_BUILDER_LOG_LEVEL",
    "AGENTIC_BUILDER_AGENT_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def isolate_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test against a clean environment.

    Tests that need a value set it themselves with ``monkeypatch.setenv``.
    """
    for name in _SETTINGS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


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

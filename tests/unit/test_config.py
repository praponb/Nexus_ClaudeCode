from __future__ import annotations

import pytest
from pydantic import SecretStr

from agentic_builder.config import ModelProvider, Settings, mask_secrets, validate_model_config
from agentic_builder.errors import ConfigError


def test_default_provider_is_moonshot_kimi_k3() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.MODEL_PROVIDER is ModelProvider.MOONSHOT
    assert settings.MODEL_NAME == "kimi-k3"


def test_validate_model_config_fails_without_api_key() -> None:
    settings = Settings(_env_file=None, MODEL_API_KEY=None)  # type: ignore[call-arg]
    with pytest.raises(ConfigError, match="MODEL_API_KEY is not configured"):
        validate_model_config(settings)


def test_validate_model_config_passes_with_api_key() -> None:
    settings = Settings(_env_file=None, MODEL_API_KEY=SecretStr("sk-test-key"))  # type: ignore[call-arg]
    validate_model_config(settings)  # should not raise


def test_validate_model_config_skips_check_for_fake_provider() -> None:
    settings = Settings(_env_file=None, MODEL_PROVIDER=ModelProvider.FAKE, MODEL_API_KEY=None)  # type: ignore[call-arg]
    validate_model_config(settings)  # should not raise even without a key


def test_validate_model_config_rejects_empty_model_name() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_API_KEY=SecretStr("sk-test-key"),
        MODEL_NAME="   ",
    )
    with pytest.raises(ConfigError, match="MODEL_NAME must not be empty"):
        validate_model_config(settings)


def test_reasoning_effort_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="MODEL_REASONING_EFFORT"):
        Settings(_env_file=None, MODEL_REASONING_EFFORT="ultra")  # type: ignore[call-arg]


def test_reasoning_effort_accepts_valid_values() -> None:
    for value in ("low", "high", "max"):
        settings = Settings(_env_file=None, MODEL_REASONING_EFFORT=value)  # type: ignore[call-arg]
        assert value == settings.MODEL_REASONING_EFFORT


def test_mask_secrets_redacts_configured_api_key() -> None:
    settings = Settings(_env_file=None, MODEL_API_KEY=SecretStr("sk-super-secret-value"))  # type: ignore[call-arg]
    text = "Request failed with api_key=sk-super-secret-value in the URL"
    masked = mask_secrets(text, settings)
    assert "sk-super-secret-value" not in masked
    assert "***REDACTED***" in masked


def test_mask_secrets_redacts_secret_shaped_substrings_without_settings() -> None:
    text = "Authorization: Bearer abcdEFGH12345678 failed"
    masked = mask_secrets(text)
    assert "abcdEFGH12345678" not in masked

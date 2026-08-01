from __future__ import annotations

import pytest
from pydantic import SecretStr

from agentic_builder.config import ModelProvider, Settings
from agentic_builder.errors import ConfigError
from agentic_builder.models.errors import ModelResolutionError
from agentic_builder.models.fake import FakeLlm
from agentic_builder.models.provider import ResolvingLiteLlm, build_llm


def test_build_llm_returns_fake_llm_for_fake_provider() -> None:
    settings = Settings(_env_file=None, MODEL_PROVIDER=ModelProvider.FAKE)  # type: ignore[call-arg]
    llm = build_llm(settings, "team_lead")
    assert isinstance(llm, FakeLlm)
    assert llm.model == "fake:team_lead"


def test_build_llm_raises_without_api_key_for_moonshot() -> None:
    settings = Settings(_env_file=None, MODEL_PROVIDER=ModelProvider.MOONSHOT, MODEL_API_KEY=None)  # type: ignore[call-arg]
    with pytest.raises(ConfigError):
        build_llm(settings, "frontend")


def test_build_llm_builds_moonshot_prefixed_model_id() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.MOONSHOT,
        MODEL_NAME="kimi-k3",
        MODEL_API_KEY=SecretStr("sk-test"),
    )
    llm = build_llm(settings, "backend")
    assert isinstance(llm, ResolvingLiteLlm)
    assert llm.model == "moonshot/kimi-k3"


def test_build_llm_uses_verbatim_model_id_for_litellm_provider() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        MODEL_PROVIDER=ModelProvider.LITELLM,
        MODEL_NAME="openai/gpt-4o-mini",
        MODEL_API_KEY=SecretStr("sk-test"),
    )
    llm = build_llm(settings, "qa")
    assert llm.model == "openai/gpt-4o-mini"


@pytest.mark.asyncio
async def test_resolving_lite_llm_wraps_not_found_error() -> None:
    import litellm.exceptions as lite_exc

    async def fake_super_generate(self: object, llm_request: object, stream: bool = False):  # type: ignore[no-untyped-def]
        raise lite_exc.NotFoundError("model not found", llm_provider="moonshot", model="kimi-k3")
        yield  # pragma: no cover -- unreachable, keeps this an async generator

    llm = ResolvingLiteLlm(model="moonshot/kimi-k3", api_key="sk-test")

    from google.adk.models.lite_llm import LiteLlm

    original = LiteLlm.generate_content_async
    LiteLlm.generate_content_async = fake_super_generate  # type: ignore[assignment]
    try:
        with pytest.raises(ModelResolutionError):
            async for _ in llm.generate_content_async(llm_request=object()):  # type: ignore[arg-type]
                pass
    finally:
        LiteLlm.generate_content_async = original  # type: ignore[assignment]

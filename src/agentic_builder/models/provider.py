"""Model-provider adapter: builds an ADK-compatible model for a given role.

Keeps provider-specific code (litellm exception handling, credential wiring)
isolated here rather than scattered through agent business logic, per the
spec's "Keep provider-specific code out of agent business logic" requirement.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.models.lite_llm import LiteLlm

from agentic_builder.config import ModelProvider, Settings, mask_secrets, validate_model_config
from agentic_builder.models.errors import ModelResolutionError
from agentic_builder.models.fake import FakeLlm

#: litellm exception classes that indicate the model/credentials themselves
#: are the problem (as opposed to a transient network/rate-limit issue that
#: the agent's retry_config should simply retry).
_RESOLUTION_ERROR_TYPES: tuple[str, ...] = (
    "NotFoundError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "UnsupportedParamsError",
    "InvalidRequestError",
)


class ResolvingLiteLlm(LiteLlm):
    """LiteLlm wrapper that turns model/credential rejections into
    ``ModelResolutionError`` instead of retrying against a silently
    different model.
    """

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        try:
            async for response in super().generate_content_async(llm_request, stream=stream):
                yield response
        except Exception as exc:  # noqa: BLE001 -- re-raised as a typed, masked error below
            if type(exc).__name__ in _RESOLUTION_ERROR_TYPES:
                raise ModelResolutionError(
                    f"Model {self.model!r} was rejected by the provider "
                    f"({type(exc).__name__}): {mask_secrets(str(exc))}"
                ) from exc
            raise


def build_llm(settings: Settings, role: str) -> BaseLlm:
    """Build the model to use for ``role`` ("team_lead", "frontend", "backend", "qa").

    Returns the deterministic ``FakeLlm`` test double when
    ``MODEL_PROVIDER=fake`` (no network access, used by the orchestrator's
    own offline test suite); otherwise validates configuration and returns a
    ``ResolvingLiteLlm`` pointed at the configured provider/model.
    """
    if settings.MODEL_PROVIDER is ModelProvider.FAKE:
        return FakeLlm(model=f"fake:{role}")

    validate_model_config(settings)

    if settings.MODEL_PROVIDER is ModelProvider.MOONSHOT:
        # litellm ships a built-in "moonshot" provider that already defaults
        # api_base to https://api.moonshot.ai/v1 and reads MOONSHOT_API_KEY;
        # see ASSUMPTIONS.md for the verification behind this route.
        model_id = f"moonshot/{settings.MODEL_NAME}"
    else:
        model_id = settings.MODEL_NAME

    kwargs: dict[str, Any] = {}
    if settings.MODEL_API_BASE:
        kwargs["api_base"] = settings.MODEL_API_BASE
    if settings.MODEL_API_KEY is not None:
        kwargs["api_key"] = settings.MODEL_API_KEY.get_secret_value()
    if settings.MODEL_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.MODEL_REASONING_EFFORT
        # litellm's built-in "moonshot" provider config doesn't list
        # reasoning_effort as supported and rejects it with
        # UnsupportedParamsError by default, even though Moonshot's actual
        # API accepts it (see ASSUMPTIONS.md / kimi-k3 quickstart). This
        # tells litellm to forward it dynamically instead of dropping or
        # rejecting it.
        kwargs["allowed_openai_params"] = ["reasoning_effort"]

    return ResolvingLiteLlm(model=model_id, **kwargs)

from __future__ import annotations

import json

import pytest
from google.adk.models import LlmRequest
from google.genai import types

from agentic_builder.models.fake import FakeLlm


def _user_content(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _function_response_content(name: str, response: dict) -> types.Content:
    return types.Content(
        role="user",
        parts=[types.Part(function_response=types.FunctionResponse(name=name, response=response))],
    )


@pytest.mark.asyncio
async def test_team_lead_first_turn_emits_publish_design_and_plan_call() -> None:
    llm = FakeLlm(model="fake:team_lead")
    request = LlmRequest(
        model=llm.model, contents=[_user_content("Cycle: 1\nMode: initial_design\nDo it.")]
    )
    responses = [r async for r in llm.generate_content_async(request)]
    assert len(responses) == 1
    call = responses[0].content.parts[0].function_call
    assert call.name == "publish_design_and_plan"
    requirements = json.loads(call.args["requirements_json"])
    assert requirements[0]["req_id"] == "REQ-1"


@pytest.mark.asyncio
async def test_team_lead_second_turn_emits_final_text() -> None:
    llm = FakeLlm(model="fake:team_lead")
    request = LlmRequest(
        model=llm.model,
        contents=[
            _user_content("Cycle: 1\nMode: initial_design\nDo it."),
            types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(name="publish_design_and_plan", args={})
                    )
                ],
            ),
            _function_response_content("publish_design_and_plan", {"design_path": "x"}),
        ],
    )
    responses = [r async for r in llm.generate_content_async(request)]
    assert len(responses) == 1
    assert responses[0].content.parts[0].text is not None
    assert responses[0].content.parts[0].function_call is None


@pytest.mark.asyncio
async def test_cycle_number_tracks_latest_turn_not_full_history() -> None:
    llm = FakeLlm(model="fake:frontend")
    request = LlmRequest(
        model=llm.model,
        contents=[
            _user_content("Cycle: 1\nDo cycle 1 work."),
            types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(name="write_frontend_files", args={})
                    )
                ],
            ),
            _function_response_content("write_frontend_files", {"written": ["frontend/README.md"]}),
            _user_content("Cycle: 2\nDo cycle 2 work."),
        ],
    )
    responses = [r async for r in llm.generate_content_async(request)]
    call = responses[0].content.parts[0].function_call
    files = json.loads(call.args["files_json"])
    assert any("cycle 2" in content for content in files.values())


@pytest.mark.asyncio
async def test_qa_design_phase_calls_write_testcase_files() -> None:
    llm = FakeLlm(model="fake:qa")
    request = LlmRequest(model=llm.model, contents=[_user_content("Cycle: 1\nPhase: design\nGo.")])
    responses = [r async for r in llm.generate_content_async(request)]
    assert responses[0].content.parts[0].function_call.name == "write_testcase_files"


@pytest.mark.asyncio
async def test_qa_execute_phase_calls_write_qa_execution_report() -> None:
    llm = FakeLlm(model="fake:qa")
    request = LlmRequest(model=llm.model, contents=[_user_content("Cycle: 1\nPhase: execute\nGo.")])
    responses = [r async for r in llm.generate_content_async(request)]
    assert responses[0].content.parts[0].function_call.name == "write_qa_execution_report"

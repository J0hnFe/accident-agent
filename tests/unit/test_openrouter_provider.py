import json
from typing import Any

import httpx
import pytest
import respx

from accident_agent.core.llm import (
    AuthenticationError,
    InvalidResponseError,
    Message,
    ProviderUnavailableError,
    RateLimitError,
    ToolCall,
)
from accident_agent.core.tool import ToolSpec
from accident_agent.providers.openrouter import OpenRouterProvider

URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["modelo/a:free", "modelo/b:free"]
TOOLS = [ToolSpec(name="get_current_time", description="Hora", parameters={"type": "object"})]
MESSAGES = [Message(role="system", content="sistema"), Message(role="user", content="hora?")]


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _provider(time: FakeTime, **kwargs: Any) -> OpenRouterProvider:
    options: dict[str, Any] = {
        "api_key": "sk-or-v1-test",
        "models": MODELS,
        "timeout_seconds": 5,
        "max_retries": 1,
        "sleep": time.sleep,
        "monotonic": time.monotonic,
    }
    options.update(kwargs)
    return OpenRouterProvider(**options)


def _ok(model: str, message: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": model,
            "choices": [{"message": message, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


def _rate_limited(retry_after: str | None = None) -> httpx.Response:
    headers = {"Retry-After": retry_after} if retry_after else {}
    return httpx.Response(429, headers=headers, json={"error": {"code": 429, "message": "Rate"}})


@respx.mock
def test_text_answer_and_request_format() -> None:
    route = respx.post(URL).mock(return_value=_ok("modelo/a:free", {"content": "Son las 12:30."}))
    result = _provider(FakeTime()).complete(MESSAGES, TOOLS)
    assert (result.content, result.tool_calls, result.model) == (
        "Son las 12:30.",
        [],
        "modelo/a:free",
    )
    assert result.usage.total_tokens == 15
    assert result.retries == 0
    request = route.calls[0].request
    body = json.loads(request.content)
    assert request.headers["Authorization"] == "Bearer sk-or-v1-test"
    assert body["model"] == "modelo/a:free"
    assert body["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Hora",
                "parameters": {"type": "object"},
            },
        }
    ]
    assert body["tool_choice"] == "auto"
    assert body["messages"] == [
        {"role": "system", "content": "sistema"},
        {"role": "user", "content": "hora?"},
    ]


@respx.mock
def test_tool_calls_are_parsed() -> None:
    respx.post(URL).mock(
        return_value=_ok(
            "modelo/a:free",
            {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_current_time", "arguments": '{"timezone":"UTC"}'},
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "search_accidents",
                            "arguments": {"province": "Guayas"},
                        },
                    },
                ],
            },
        )
    )
    result = _provider(FakeTime()).complete(MESSAGES, TOOLS)
    assert result.tool_calls == [
        ToolCall(id="call_1", name="get_current_time", arguments='{"timezone":"UTC"}'),
        ToolCall(id="call_2", name="search_accidents", arguments='{"province": "Guayas"}'),
    ]


@respx.mock
def test_assistant_and_tool_messages_are_serialized() -> None:
    route = respx.post(URL).mock(return_value=_ok("modelo/a:free", {"content": "listo"}))
    history = [
        *MESSAGES,
        Message(
            role="assistant",
            tool_calls=[ToolCall(id="call_1", name="get_current_time", arguments="{}")],
        ),
        Message(role="tool", tool_call_id="call_1", content='{"ok": true}'),
    ]
    _provider(FakeTime()).complete(history, TOOLS)
    sent = json.loads(route.calls[0].request.content)["messages"]
    assert sent[2] == {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "get_current_time", "arguments": "{}"},
            }
        ],
    }
    assert sent[3] == {"role": "tool", "tool_call_id": "call_1", "content": '{"ok": true}'}


@respx.mock
def test_rate_limit_retries_honoring_retry_after() -> None:
    respx.post(URL).mock(side_effect=[_rate_limited("3"), _ok("modelo/a:free", {"content": "ok"})])
    time = FakeTime()
    result = _provider(time).complete(MESSAGES, TOOLS)
    assert result.content == "ok"
    assert result.retries == 1
    assert time.sleeps == [3.0]


@respx.mock
def test_falls_back_to_next_model_after_retries() -> None:
    route = respx.post(URL).mock(
        side_effect=[_rate_limited(), _rate_limited(), _ok("modelo/b:free", {"content": "ok"})]
    )
    time = FakeTime()
    result = _provider(time).complete(MESSAGES, TOOLS)
    assert (result.model, result.retries) == ("modelo/b:free", 2)
    models = [json.loads(c.request.content)["model"] for c in route.calls]
    assert models == ["modelo/a:free", "modelo/a:free", "modelo/b:free"]
    assert time.sleeps == [1.0]  # backoff exponencial sin Retry-After


@respx.mock
def test_all_models_rate_limited() -> None:
    respx.post(URL).mock(return_value=_rate_limited("2"))
    with pytest.raises(RateLimitError):
        _provider(FakeTime()).complete(MESSAGES, TOOLS)


@respx.mock
def test_long_retry_after_skips_to_next_model_without_waiting() -> None:
    respx.post(URL).mock(
        side_effect=[_rate_limited("120"), _ok("modelo/b:free", {"content": "ok"})]
    )
    time = FakeTime()
    result = _provider(time).complete(MESSAGES, TOOLS)
    assert result.model == "modelo/b:free"
    assert time.sleeps == []


@respx.mock
def test_authentication_error_does_not_try_other_models() -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(401, json={"error": {"message": "No auth"}})
    )
    with pytest.raises(AuthenticationError):
        _provider(FakeTime()).complete(MESSAGES, TOOLS)
    assert route.call_count == 1


def test_missing_api_key_fails_before_calling() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(URL)
        with pytest.raises(AuthenticationError, match="OPENROUTER_API_KEY"):
            _provider(FakeTime(), api_key="").complete(MESSAGES, TOOLS)
        assert route.call_count == 0


@respx.mock
def test_timeout_and_server_errors_fall_back() -> None:
    respx.post(URL).mock(
        side_effect=[
            httpx.ReadTimeout("lento"),
            httpx.Response(503, json={"error": {"message": "caido"}}),
            _ok("modelo/b:free", {"content": "ok"}),
        ]
    )
    result = _provider(FakeTime()).complete(MESSAGES, TOOLS)
    assert (result.model, result.retries) == ("modelo/b:free", 2)


@respx.mock
def test_all_models_unavailable() -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("sin red"))
    with pytest.raises(ProviderUnavailableError):
        _provider(FakeTime()).complete(MESSAGES, TOOLS)


@pytest.mark.parametrize(
    "body",
    [
        {"choices": []},
        {"choices": [{"message": {"tool_calls": [{"id": "x", "function": {"arguments": "{}"}}]}}]},
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [{"id": "x", "function": {"name": "a", "arguments": 5}}]
                    }
                }
            ]
        },
    ],
)
def test_malformed_responses_try_the_next_model(body: dict[str, Any]) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=body))
        with pytest.raises(InvalidResponseError):
            _provider(FakeTime()).complete(MESSAGES, TOOLS)
        # Reintentar con el mismo modelo daria el mismo formato: un intento por modelo.
        assert route.call_count == len(MODELS)


@respx.mock
def test_error_inside_a_200_is_transient_and_retried() -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"error": {"code": 502, "message": "upstream"}})
    )
    with pytest.raises(ProviderUnavailableError):
        _provider(FakeTime()).complete(MESSAGES, TOOLS)
    assert route.call_count == 2 * len(MODELS)


@respx.mock
def test_missing_tool_call_id_is_generated() -> None:
    respx.post(URL).mock(
        return_value=_ok(
            "modelo/a:free",
            {"tool_calls": [{"function": {"name": "get_current_time", "arguments": ""}}]},
        )
    )
    call = _provider(FakeTime()).complete(MESSAGES, TOOLS).tool_calls[0]
    assert call.id
    assert call.arguments == "{}"


@respx.mock
def test_total_budget_stops_retries() -> None:
    respx.post(URL).mock(return_value=_rate_limited("4"))
    time = FakeTime()
    with pytest.raises(RateLimitError):
        _provider(time, total_budget_seconds=5).complete(MESSAGES, TOOLS)
    assert sum(time.sleeps) <= 5

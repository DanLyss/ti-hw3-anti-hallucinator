import json

import httpx
import pytest

from src.llm_clients import http_utils
from src.llm_clients.openai_compatible import OpenAICompatibleClient


def test_generate_sends_prompt_and_returns_content():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-x"
        assert payload["messages"] == [{"role": "user", "content": "hello"}]
        assert payload["max_tokens"] == 123
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": "n\nm\n..."}}]})

    client = OpenAICompatibleClient(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="gpt-x",
        max_tokens=123,
        transport=httpx.MockTransport(handler),
    )
    assert client.generate("hello") == "n\nm\n..."


def test_generate_returns_empty_string_when_content_is_null():
    # Модель может выработать весь max_tokens на reasoning и не оставить ничего на content
    # (finish_reason="length", content=null) — это валидный результат, а не сбой запроса.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "length", "message": {"content": None}}]},
        )

    client = OpenAICompatibleClient(
        base_url="https://example.test/v1",
        api_key="k",
        model_name="m",
        transport=httpx.MockTransport(handler),
    )
    assert client.generate("hi") == ""


def test_generate_retries_on_5xx_then_succeeds(monkeypatch):
    monkeypatch.setattr(http_utils.time, "sleep", lambda seconds: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500)
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK after retries"}}]})

    client = OpenAICompatibleClient(
        base_url="https://example.test/v1",
        api_key="k",
        model_name="m",
        transport=httpx.MockTransport(handler),
    )
    assert client.generate("hi") == "OK after retries"
    assert calls["n"] == 3


def test_generate_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr(http_utils.time, "sleep", lambda seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = OpenAICompatibleClient(
        base_url="https://example.test/v1",
        api_key="k",
        model_name="m",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(httpx.HTTPStatusError):
        client.generate("hi")

import json
import time

import httpx
import pytest

from src.llm_clients import http_utils
from src.llm_clients.gigachat_client import GigaChatClient
from src.llm_clients.openai_compatible import OpenAICompatibleClient


def test_generate_sends_prompt_and_returns_content():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-x"
        assert payload["messages"] == [{"role": "user", "content": "hello"}]
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": "n\nm\n..."}}]})

    client = OpenAICompatibleClient(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="gpt-x",
        transport=httpx.MockTransport(handler),
    )
    assert client.generate("hello") == "n\nm\n..."


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


def test_gigachat_fetches_token_once_and_reuses_it():
    calls = {"oauth": 0, "chat": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.test/oauth":
            calls["oauth"] += 1
            return httpx.Response(
                200,
                json={"access_token": "tok-1", "expires_at": int((time.time() + 3600) * 1000)},
            )
        calls["chat"] += 1
        assert request.headers["Authorization"] == "Bearer tok-1"
        return httpx.Response(200, json={"choices": [{"message": {"content": "giga answer"}}]})

    client = GigaChatClient(
        client_id="id",
        client_secret="secret",
        model_name="GigaChat",
        oauth_url="https://example.test/oauth",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )
    assert client.generate("q1") == "giga answer"
    assert client.generate("q2") == "giga answer"
    assert calls["oauth"] == 1
    assert calls["chat"] == 2


def test_gigachat_refreshes_an_already_expired_token():
    calls = {"oauth": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.test/oauth":
            calls["oauth"] += 1
            # expires_at = "сейчас" -> с учётом запаса токен всегда считается истёкшим
            return httpx.Response(200, json={"access_token": f"tok-{calls['oauth']}", "expires_at": int(time.time() * 1000)})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = GigaChatClient(
        client_id="id",
        client_secret="secret",
        model_name="GigaChat",
        oauth_url="https://example.test/oauth",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )
    client.generate("a")
    client.generate("b")
    assert calls["oauth"] == 2

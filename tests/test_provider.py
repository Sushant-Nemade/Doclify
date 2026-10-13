import httpx
import pytest
from groq import Groq

from doclify.schema.schema import LLMConfig
from doclify.utils import llm


def test_sdk_request_uses_fixed_origin_and_bounded_tokens(monkeypatch):
    captured = []

    def response(request):
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 1,
                "model": "fixture-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "A bounded summary."},
                    }
                ],
            },
        )

    def client(config):
        return Groq(
            api_key="fixture",
            base_url="https://api.groq.com",
            max_retries=0,
            http_client=httpx.Client(
                transport=httpx.MockTransport(response), follow_redirects=False
            ),
        )

    monkeypatch.setattr(llm, "create_client", client)
    result = llm.generate_doc("print('hello')", "batch_summary", LLMConfig(max_tokens=128))
    assert result == "A bounded summary."
    assert len(captured) == 1
    assert captured[0].url.host == "api.groq.com"
    assert captured[0].url.path == "/openai/v1/chat/completions"
    assert b'"max_tokens":128' in captured[0].content


def test_provider_error_does_not_expose_response_or_credential(monkeypatch):
    def response(request):
        return httpx.Response(
            401,
            json={"error": {"message": "private-provider-payload", "type": "authentication_error"}},
        )

    def client(config):
        return Groq(
            api_key="fixture",
            base_url="https://api.groq.com",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(response)),
        )

    monkeypatch.setattr(llm, "create_client", client)
    with pytest.raises(ValueError) as captured:
        llm.generate_doc("safe", "batch_summary")
    assert "private-provider-payload" not in str(captured.value)
    assert "fixture" not in str(captured.value)


def test_client_disables_redirects_and_bounds_retries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "fixture")
    with llm.create_client(LLMConfig(timeout=7, max_retries=1)) as client:
        assert client.base_url.host == "api.groq.com"
        assert client.max_retries == 1
        assert client._client.follow_redirects is False
        assert client._client.timeout.read == 7


def test_unknown_prompt_cannot_escape_packaged_resources():
    from doclify.utils.utils import get_prompt

    with pytest.raises(ValueError):
        get_prompt("../../outside")

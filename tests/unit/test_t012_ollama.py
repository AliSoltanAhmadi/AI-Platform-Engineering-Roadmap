import json
import socket
from urllib.error import URLError

import pytest

from llm.model_selector import ModelSelector
from llm.ollama_client import (
    OllamaClient,
    OllamaInvalidResponseError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    OllamaUnsafeEndpointError,
)
from session import Session


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.payload


def test_api_tags_discovers_installed_model_names():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return FakeResponse(
            {
                "models": [
                    {"name": "llama3.2:latest", "model": "llama3.2:latest"},
                    {"model": "qwen3:4b"},
                ]
            }
        )

    client = OllamaClient(timeout=0.25, opener=opener)

    assert client.list_models() == ["llama3.2:latest", "qwen3:4b"]
    assert calls[0][0].full_url == "http://localhost:11434/api/tags"
    assert calls[0][0].get_method() == "GET"
    assert calls[0][1] == 0.25


@pytest.mark.parametrize(
    ("failure", "error_type"),
    [
        (socket.timeout("slow"), OllamaTimeoutError),
        (URLError(socket.timeout("wrapped slow")), OllamaTimeoutError),
        (URLError("offline"), OllamaUnavailableError),
    ],
)
def test_timeout_and_unavailable_service_are_controlled(failure, error_type):
    def opener(_request, timeout=None):
        raise failure

    with pytest.raises(error_type):
        OllamaClient(opener=opener).list_models()


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        {"unexpected": []},
        {"models": [{"size": 123}]},
    ],
)
def test_invalid_tag_responses_are_rejected(payload):
    client = OllamaClient(opener=lambda _request, timeout=None: FakeResponse(payload))

    with pytest.raises(OllamaInvalidResponseError):
        client.list_models()


def test_remote_ollama_endpoint_is_rejected():
    with pytest.raises(OllamaUnsafeEndpointError, match="loopback"):
        OllamaClient("https://example.com:11434")


def test_generate_uses_non_streaming_knowledge_base_grounded_prompt():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"model": "llama3.2", "response": "Use docker compose.", "done": True})

    client = OllamaClient(opener=opener)
    response = client.generate_grounded(
        "llama3.2",
        "How do I pull an image?",
        "Phase: P0 Bridge\nNext step: Run docker compose.",
    )

    assert response == "Use docker compose."
    assert captured["url"].endswith("/api/generate")
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["model"] == "llama3.2"
    assert "P0 Bridge" in captured["payload"]["prompt"]
    assert "How do I pull an image?" in captured["payload"]["prompt"]
    assert "Use only the supplied LOCAL KNOWLEDGE BASE" in captured["payload"]["system"]


def test_selector_falls_back_for_invalid_ollama_response():
    client = OllamaClient(opener=lambda _request, timeout=None: FakeResponse({"bad": []}))
    selector = ModelSelector(ollama_client=client)

    selector.vllm.list_models = lambda: []
    assert selector.select() == ("deterministic", "knowledge-base-v1")
    assert "models array" in selector.last_error


def test_session_sends_only_matched_local_topic_context_to_ollama(tmp_path):
    class RecordingClient:
        def __init__(self):
            self.calls = []

        def list_models(self):
            return ["local-model"]

        def generate_grounded(self, model, question, context):
            self.calls.append((model, question, context))
            return "Grounded local explanation."

    client = RecordingClient()
    selector = ModelSelector(ollama_client=client)
    session = Session(state_path=tmp_path / "progress.json", model_selector=selector)
    assert session.select_model() == ("ollama", "local-model")

    answer = session.answer_roadmap_question("How do I pull an image?")

    assert answer.model_response == "Grounded local explanation."
    model, question, context = client.calls[0]
    assert model == "local-model"
    assert question == "How do I pull an image?"
    assert "Phase: P0 Bridge" in context
    assert "Next step:" in context
    assert "RAG infrastructure" not in context

    out_of_scope = session.answer_roadmap_question("weather on Mars")
    assert out_of_scope.status == "out_of_scope"
    assert len(client.calls) == 1

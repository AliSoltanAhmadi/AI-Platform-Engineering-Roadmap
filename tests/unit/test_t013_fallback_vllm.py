import argparse
import json
from urllib.error import URLError
from urllib.parse import urlparse
from unittest.mock import patch

import pytest

from llm.bundled_model import BundledModel
from llm.model_selector import ModelSelector
from llm.ollama_client import OllamaUnavailableError
from llm.vllm_client import (
    VllmClient,
    VllmInvalidResponseError,
    VllmUnsafeEndpointError,
)
from session import Session, run_cli


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.payload


def test_deterministic_fallback_is_repeatable_and_knowledge_base_grounded():
    model = BundledModel()
    context = (
        "Phase: P0 Bridge\n"
        "Simple explanation: Images are downloaded from a registry.\n"
        "Next step: Pull nginx locally."
    )

    first = model.respond_grounded("How?", context)
    second = model.respond_grounded("Different wording", context)

    assert first == second
    assert first == "Images are downloaded from a registry. Next, Pull nginx locally."
    assert "Acknowledged" not in first


def test_selector_uses_vllm_after_ollama_then_deterministic_if_both_absent():
    selector = ModelSelector()
    selector.ollama.list_models = lambda: (_ for _ in ()).throw(
        OllamaUnavailableError("offline")
    )
    selector.vllm.list_models = lambda: ["local-vllm-model"]

    assert selector.select() == ("vllm", "local-vllm-model")

    selector.vllm.list_models = lambda: []
    assert selector.select() == ("deterministic", "knowledge-base-v1")


def test_vllm_discovers_models_and_generates_grounded_chat_completion():
    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        if request.full_url.endswith("/v1/models"):
            return FakeResponse({"object": "list", "data": [{"id": "model-a"}]})
        return FakeResponse(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "Grounded answer."}}
                ]
            }
        )

    client = VllmClient(opener=opener)

    assert client.list_models() == ["model-a"]
    assert client.generate_grounded("model-a", "Question", "Phase: P0 local context") == "Grounded answer."
    payload = json.loads(requests[1][0].data.decode("utf-8"))
    assert requests[0][0].full_url == "http://localhost:8000/v1/models"
    assert requests[1][0].full_url.endswith("/v1/chat/completions")
    assert payload["stream"] is False
    assert payload["temperature"] == 0
    assert "P0 local context" in payload["messages"][1]["content"]
    assert "Use only the supplied LOCAL KNOWLEDGE BASE" in payload["messages"][0]["content"]


def test_vllm_rejects_remote_and_invalid_responses():
    with pytest.raises(VllmUnsafeEndpointError, match="loopback"):
        VllmClient("https://remote.example")

    client = VllmClient(opener=lambda _request, timeout=None: FakeResponse({"data": [{}]}))
    with pytest.raises(VllmInvalidResponseError):
        client.list_models()


def test_local_generation_failure_uses_deterministic_answer(tmp_path):
    class FailingOllama:
        def list_models(self):
            return ["local-model"]

        def generate_grounded(self, _model, _question, _context):
            raise OllamaUnavailableError("stopped")

    selector = ModelSelector(ollama_client=FailingOllama())
    session = Session(state_path=tmp_path / "progress.json", model_selector=selector)
    assert session.select_model() == ("ollama", "local-model")

    answer = session.answer_roadmap_question("How do I pull an image?")

    assert answer.status == "matched"
    assert answer.model_response
    assert answer.explanation in answer.model_response
    assert "Acknowledged" not in answer.model_response


def test_main_flow_never_attempts_a_non_loopback_request(tmp_path):
    urls = []

    def refuse_local(_opener, request, data=None, timeout=None):
        urls.append(request.full_url)
        raise URLError("local service is off")

    args = argparse.Namespace(
        state_path=str(tmp_path / "progress.json"),
        level=None,
        answer=None,
        non_interactive=False,
    )
    choices = iter(["5"])
    output = []

    with patch("urllib.request.OpenerDirector.open", new=refuse_local):
        code = run_cli(args, input_fn=lambda _prompt: next(choices), output=output.append)

    assert code == 0
    assert {urlparse(url).hostname for url in urls} <= {"localhost", "127.0.0.1", "::1"}
    assert urls == ["http://localhost:11434/api/tags", "http://localhost:8000/v1/models"]
    assert "Active local model: deterministic/knowledge-base-v1" in "\n".join(output)


def test_no_local_model_server_does_not_block_scoring_or_persistence(tmp_path):
    state_path = tmp_path / "progress.json"
    urls = []

    def refuse_local(_opener, request, data=None, timeout=None):
        urls.append(request.full_url)
        raise URLError("local service is off")

    args = argparse.Namespace(
        state_path=str(state_path),
        level="beginner",
        answer="docker pull nginx",
        non_interactive=True,
    )
    output = []

    with patch("urllib.request.OpenerDirector.open", new=refuse_local):
        code = run_cli(args, output=output.append)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert code == 0
    assert state["completed_lessons"] == ["beginner-first-task"]
    assert state["attempts"] == 1
    assert "Correct. Progress saved." in "\n".join(output)
    assert all(urlparse(url).hostname in {"localhost", "127.0.0.1", "::1"} for url in urls)

import sys
sys.path.insert(0, "src")
from unittest.mock import patch
from llm.model_selector import ModelSelector
from llm.bundled_model import BundledModel
from llm.ollama_client import OllamaTimeoutError

def test_model_selector_prefers_available_ollama():
    selector = ModelSelector()
    with patch.object(selector.ollama, "list_models", return_value=["llama3.2"]), patch.object(
        selector.vllm, "list_models"
    ) as vllm_models:
        backend, model = selector.select()
    assert backend == "ollama"
    assert model == "llama3.2"
    vllm_models.assert_not_called()

def test_model_selector_uses_deterministic_fallback():
    selector = ModelSelector()
    with patch.object(
        selector.ollama, "list_models", side_effect=OllamaTimeoutError("timeout")
    ), patch.object(selector.vllm, "list_models", return_value=[]):
        backend, model = selector.select()
    assert backend == "deterministic"
    assert model == "knowledge-base-v1"
    assert isinstance(selector.bundled, BundledModel)
    response = selector.bundled.respond_grounded(
        "question",
        "Simple explanation: Local explanation.\nNext step: Run the local exercise.",
    )
    assert response == "Local explanation. Next, Run the local exercise."

def test_module_smoke_import_llm_modules():
    import llm.bundled_model
    import llm.ollama_client
    import llm.model_selector
    import llm.vllm_client

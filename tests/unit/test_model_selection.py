import sys
sys.path.insert(0, "src")
from unittest.mock import patch
from llm.model_selector import ModelSelector
from llm.bundled_model import BundledModel

def test_model_selector_prefers_available_ollama():
    selector = ModelSelector()
    with patch.object(selector.ollama, "list_models", return_value=["llama3.2"]):
        backend, model = selector.select()
    assert backend == "ollama"
    assert model == "llama3.2"

def test_model_selector_uses_bundled_fallback():
    selector = ModelSelector()
    with patch.object(selector.ollama, "list_models", side_effect=Exception("timeout")):
        backend, model = selector.select()
    assert backend == "bundled"
    assert model == "bundled-fallback"
    assert isinstance(selector.bundled, BundledModel)
    assert selector.bundled.respond("offline")

def test_module_smoke_import_llm_modules():
    import llm.bundled_model
    import llm.ollama_client
    import llm.model_selector

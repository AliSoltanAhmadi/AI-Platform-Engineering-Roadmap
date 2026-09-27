#!/usr/bin/env python3
"""Select Ollama, then vLLM, then the deterministic Knowledge Base fallback."""
from llm.bundled_model import BundledModel
from llm.ollama_client import OllamaClient, OllamaError
from llm.vllm_client import VllmClient, VllmError


class ModelSelector:
    def __init__(
        self,
        ollama_url="http://localhost:11434",
        vllm_url="http://localhost:8000",
        ollama_client=None,
        vllm_client=None,
    ):
        self.ollama = ollama_client or OllamaClient(base_url=ollama_url)
        self.vllm = vllm_client or VllmClient(base_url=vllm_url)
        self.bundled = BundledModel()
        self.backend = None
        self.model = None
        self.last_error = None

    def select(self):
        errors = []
        try:
            models = self.ollama.list_models()
            if models:
                return self._activate("ollama", models[0], errors)
        except OllamaError as exc:
            errors.append(str(exc))

        try:
            models = self.vllm.list_models()
            if models:
                return self._activate("vllm", models[0], errors)
        except VllmError as exc:
            errors.append(str(exc))

        return self._activate("deterministic", self.bundled.name, errors)

    def _activate(self, backend, model, errors):
        self.backend = backend
        self.model = model
        self.last_error = "; ".join(errors) or None
        return backend, model

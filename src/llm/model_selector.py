#!/usr/bin/env python3
from llm.ollama_client import OllamaClient
from llm.bundled_model import BundledModel

class ModelSelector:
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama = OllamaClient(base_url=ollama_url)
        self.bundled = BundledModel()
        self.backend = None
        self.model = None

    def select(self):
        try:
            models = self.ollama.list_models()
            if models:
                self.backend = "ollama"
                self.model = models[0]
                return ("ollama", self.model)
        except Exception:
            pass
        self.backend = "bundled"
        self.model = "bundled-fallback"
        return ("bundled", self.model)

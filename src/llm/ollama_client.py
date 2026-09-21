#!/usr/bin/env python3
"""Ollama REST client via Net.HttpClient per research.md."""
class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url

    def list_models(self):
        return []

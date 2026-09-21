#!/usr/bin/env python3
"""Bundled lightweight fallback when no preconfigured model per spec."""
class BundledModel:
    def __init__(self):
        pass

    def respond(self, prompt: str) -> str:
        return "[bundled] Acknowledged: " + prompt[:50]

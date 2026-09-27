#!/usr/bin/env python3
"""Small, dependency-free client for a loopback Ollama server."""
from __future__ import annotations

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class OllamaError(RuntimeError):
    """Base class for controlled local Ollama failures."""


class OllamaTimeoutError(OllamaError):
    pass


class OllamaUnavailableError(OllamaError):
    pass


class OllamaInvalidResponseError(OllamaError):
    pass


class OllamaUnsafeEndpointError(OllamaError):
    pass


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", timeout=0.25, opener=None):
        self.base_url = self._validate_base_url(base_url)
        self.timeout = float(timeout)
        if self.timeout <= 0:
            raise ValueError("Ollama timeout must be positive.")
        self._open = opener or build_opener(ProxyHandler({}), _NoRedirectHandler()).open

    def list_models(self):
        data = self._request("/api/tags")
        raw_models = data.get("models")
        if not isinstance(raw_models, list):
            raise OllamaInvalidResponseError("Ollama /api/tags response has no models array.")
        models = []
        for item in raw_models:
            if not isinstance(item, dict):
                raise OllamaInvalidResponseError("Ollama returned an invalid model entry.")
            name = item.get("name") or item.get("model")
            if not isinstance(name, str) or not name.strip():
                raise OllamaInvalidResponseError("Ollama returned a model without a name.")
            if name not in models:
                models.append(name)
        return models

    def generate_grounded(self, model, question, context):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("An installed Ollama model name is required.")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("A non-empty question is required.")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("Local Knowledge Base context is required.")
        prompt = (
            "LOCAL KNOWLEDGE BASE CONTEXT:\n"
            f"{context.strip()}\n\n"
            "LEARNER QUESTION:\n"
            f"{question.strip()}\n\n"
            "Answer briefly. If the context does not contain the answer, say that it is not in the local roadmap."
        )
        data = self._request(
            "/api/generate",
            {
                "model": model.strip(),
                "prompt": prompt,
                "system": (
                    "You are an offline roadmap tutor. Use only the supplied LOCAL KNOWLEDGE BASE "
                    "CONTEXT. Do not add facts from memory or external sources."
                ),
                "stream": False,
            },
        )
        response = data.get("response")
        if not isinstance(response, str) or not response.strip() or data.get("done") is not True:
            raise OllamaInvalidResponseError("Ollama returned an incomplete generation response.")
        return response.strip()

    def _request(self, path, payload=None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST" if body is not None else "GET",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with self._open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (socket.timeout, TimeoutError) as exc:
            raise OllamaTimeoutError("Ollama did not respond before the local timeout.") from exc
        except URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise OllamaTimeoutError("Ollama did not respond before the local timeout.") from exc
            raise OllamaUnavailableError("Ollama is not available on the local endpoint.") from exc
        except (HTTPError, OSError) as exc:
            raise OllamaUnavailableError("Ollama is not available on the local endpoint.") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise OllamaInvalidResponseError("Ollama response exceeded the safe size limit.")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaInvalidResponseError("Ollama returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise OllamaInvalidResponseError("Ollama response must be a JSON object.")
        return data

    @staticmethod
    def _validate_base_url(base_url):
        parsed = urlparse(str(base_url).rstrip("/"))
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in LOCAL_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise OllamaUnsafeEndpointError("Ollama endpoint must be an HTTP(S) loopback URL.")
        return str(base_url).rstrip("/")

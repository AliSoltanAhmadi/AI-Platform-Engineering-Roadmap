#!/usr/bin/env python3
"""Loopback-only client for vLLM's OpenAI-compatible server."""
from __future__ import annotations

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class VllmError(RuntimeError):
    pass


class VllmTimeoutError(VllmError):
    pass


class VllmUnavailableError(VllmError):
    pass


class VllmInvalidResponseError(VllmError):
    pass


class VllmUnsafeEndpointError(VllmError):
    pass


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VllmClient:
    def __init__(self, base_url="http://localhost:8000", timeout=0.25, opener=None):
        self.base_url = self._validate_base_url(base_url)
        self.timeout = float(timeout)
        if self.timeout <= 0:
            raise ValueError("vLLM timeout must be positive.")
        self._open = opener or build_opener(ProxyHandler({}), _NoRedirectHandler()).open

    def list_models(self):
        data = self._request("/v1/models")
        entries = data.get("data")
        if not isinstance(entries, list):
            raise VllmInvalidResponseError("vLLM /v1/models response has no data array.")
        models = []
        for item in entries:
            model_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(model_id, str) or not model_id.strip():
                raise VllmInvalidResponseError("vLLM returned a model without an id.")
            if model_id not in models:
                models.append(model_id)
        return models

    def generate_grounded(self, model, question, context):
        if not all(isinstance(value, str) and value.strip() for value in (model, question, context)):
            raise ValueError("Model, question, and local context are required.")
        system = (
            "You are an offline roadmap tutor. Use only the supplied LOCAL KNOWLEDGE BASE "
            "CONTEXT. Do not add facts from memory or external sources."
        )
        user = (
            f"LOCAL KNOWLEDGE BASE CONTEXT:\n{context.strip()}\n\n"
            f"LEARNER QUESTION:\n{question.strip()}\n\n"
            "Answer briefly; say when the local context is insufficient."
        )
        data = self._request(
            "/v1/chat/completions",
            {
                "model": model.strip(),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
                "stream": False,
            },
        )
        choices = data.get("choices")
        try:
            content = choices[0]["message"]["content"]
        except (IndexError, KeyError, TypeError):
            content = None
        if not isinstance(content, str) or not content.strip():
            raise VllmInvalidResponseError("vLLM returned an invalid chat completion.")
        return content.strip()

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
            raise VllmTimeoutError("vLLM did not respond before the local timeout.") from exc
        except URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise VllmTimeoutError("vLLM did not respond before the local timeout.") from exc
            raise VllmUnavailableError("vLLM is not available on the local endpoint.") from exc
        except (HTTPError, OSError) as exc:
            raise VllmUnavailableError("vLLM is not available on the local endpoint.") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise VllmInvalidResponseError("vLLM response exceeded the safe size limit.")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VllmInvalidResponseError("vLLM returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise VllmInvalidResponseError("vLLM response must be a JSON object.")
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
            raise VllmUnsafeEndpointError("vLLM endpoint must be an HTTP(S) loopback URL.")
        return str(base_url).rstrip("/")

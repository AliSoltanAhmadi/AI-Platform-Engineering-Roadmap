#!/usr/bin/env python3
"""Deterministic, offline roadmap question routing."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parents[2] / "content" / "knowledge-base.json"
MAX_QUERY_LENGTH = 300
TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
STOP_WORDS = {
    "a", "an", "and", "are", "can", "do", "for", "how", "i", "in", "is", "it",
    "of", "on", "the", "to", "what", "with", "از", "با", "برای", "به", "را", "رو",
    "من", "می", "یک", "چه", "چطور", "چگونه", "کنم", "است",
}

TOPIC_ALIASES = {
    "p0-bridge-docker-compose-fastapi": {
        "docker", "compose", "fastapi", "container", "image", "pull", "podman",
        "کانتینر", "ایمیج", "تصویر",
    },
    "p0-bridge-pod-deployment-service": {
        "pod", "deployment", "service", "kubernetes", "kubectl", "پاد", "سرویس",
    },
    "p1-ml-literacy-python": {"python", "pandas", "numpy", "csv", "scikit"},
    "p1-ml-literacy-vocabulary": {"training", "inference", "feature", "model", "آموزش", "مدل"},
    "p2-mlops-dvc": {"dvc", "dataset", "version", "data", "داده"},
    "p2-mlops-mlflow": {"mlflow", "experiment", "metric", "پارامتر", "آزمایش"},
    "p2-mlops-feast": {"feast", "feature", "store"},
    "p2-mlops-fastapi-bentoml": {"bentoml", "bento", "serving"},
    "p3-k8s-inference-service": {"kserve", "inferenceservice", "canary", "autoscaling"},
    "p3-k8s-argoworkflows": {"argo", "workflow", "job", "pipeline"},
    "p3-k8s-gitops": {"gitops", "argocd", "helm", "rollback"},
    "p4-llmops-vllm": {"vllm", "llm", "pagedattention", "throughput"},
    "p4-llmops-rag": {"rag", "retrieval", "embedding", "chunking"},
    "p4-llmops-gateway": {"gateway", "rate", "limit", "auth", "token"},
    "p4-k8s-gpu-scheduling": {"gpu", "nvidia", "dcgm", "scheduling", "گرافیک"},
}


class RoadmapContentError(ValueError):
    """Raised when the local Knowledge Base is missing or invalid."""


@dataclass(frozen=True)
class RoadmapAnswer:
    status: str
    message: str
    phase: str | None = None
    title: str | None = None
    explanation: str | None = None
    prerequisites: tuple[str, ...] = ()
    next_step_action: str | None = None
    topic_id: str | None = None
    model_response: str | None = None

    def render(self):
        if self.status != "matched":
            return self.message
        prerequisites = ", ".join(self.prerequisites) if self.prerequisites else "None"
        lines = [
                f"Phase: {self.phase}",
                f"Topic: {self.title}",
                f"Simple explanation: {self.explanation}",
                f"Prerequisites: {prerequisites}",
                f"Next step: {self.next_step_action}",
            ]
        if self.model_response:
            lines.append(f"Local model explanation: {self.model_response}")
        return "\n".join(lines)


class KnowledgeBaseLoader:
    def __init__(self, path=None):
        self.path = Path(path).resolve() if path else DEFAULT_KNOWLEDGE_PATH

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RoadmapContentError("Knowledge Base file is missing.") from exc
        except json.JSONDecodeError as exc:
            raise RoadmapContentError("Knowledge Base JSON is invalid.") from exc
        if not isinstance(data, dict) or data.get("schema_version") != "1.0.0":
            raise RoadmapContentError("Knowledge Base schema_version must be 1.0.0.")
        topics = data.get("topics")
        phase_prerequisites = data.get("phase_prerequisites")
        if not isinstance(topics, list) or not topics:
            raise RoadmapContentError("Knowledge Base must contain topics.")
        if not isinstance(phase_prerequisites, dict):
            raise RoadmapContentError("Knowledge Base must contain phase_prerequisites.")
        required = ("topic_id", "title", "phase", "explanation", "next_step_action")
        for index, topic in enumerate(topics):
            if not isinstance(topic, dict) or any(
                not isinstance(topic.get(field), str) or not topic[field].strip()
                for field in required
            ):
                raise RoadmapContentError(f"Knowledge Base topic {index} is invalid.")
            prerequisites = phase_prerequisites.get(topic["phase"])
            if not isinstance(prerequisites, list) or not all(
                isinstance(item, str) and item.strip() for item in prerequisites
            ):
                raise RoadmapContentError(
                    f"Knowledge Base prerequisites are missing for {topic['phase']}."
                )
        return data


class RoadmapExplorer:
    def __init__(self, path=None):
        self.data = KnowledgeBaseLoader(path).load()

    def ask(self, query):
        cleaned = self._clean(query)
        if not cleaned:
            return RoadmapAnswer(
                "invalid",
                "Please enter a roadmap question. Returning to the main menu.",
            )
        if len(cleaned) > MAX_QUERY_LENGTH:
            return RoadmapAnswer(
                "too_long",
                f"That question is too long (maximum {MAX_QUERY_LENGTH} characters). Returning to the main menu.",
            )

        query_tokens = self._tokens(cleaned)
        best_topic = None
        best_score = 0
        for topic in self.data["topics"]:
            searchable = " ".join(
                str(topic.get(field, ""))
                for field in ("topic_id", "title", "phase", "explanation", "next_step_action")
            )
            topic_tokens = self._tokens(searchable) | TOPIC_ALIASES.get(topic["topic_id"], set())
            overlap = query_tokens.intersection(topic_tokens)
            alias_overlap = overlap.intersection(TOPIC_ALIASES.get(topic["topic_id"], set()))
            score = len(overlap) + (2 * len(alias_overlap))
            if score > best_score:
                best_topic, best_score = topic, score

        if best_topic is None or best_score < 2:
            return RoadmapAnswer(
                "out_of_scope",
                "I could not map that question to this AI Platform Engineering roadmap. "
                "Try a topic such as Docker, DVC, Kubernetes, vLLM, RAG, or GPU scheduling, "
                "or return to the main menu.",
            )

        prerequisites = self.data["phase_prerequisites"][best_topic["phase"]]
        return RoadmapAnswer(
            status="matched",
            message="Roadmap topic found.",
            phase=best_topic["phase"],
            title=best_topic["title"],
            explanation=best_topic["explanation"],
            prerequisites=tuple(prerequisites),
            next_step_action=best_topic["next_step_action"],
            topic_id=best_topic["topic_id"],
        )

    @staticmethod
    def _clean(query):
        if not isinstance(query, str):
            return ""
        return " ".join(query.split()).strip()

    @staticmethod
    def _tokens(text):
        return {
            token
            for token in TOKEN_PATTERN.findall(text.casefold())
            if len(token) > 1 and token not in STOP_WORDS
        }

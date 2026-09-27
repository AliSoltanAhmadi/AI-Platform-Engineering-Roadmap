#!/usr/bin/env python3
"""Fixed, local pre/post assessment for SC-002."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ASSESSMENT_PATH = Path(__file__).resolve().parents[2] / "content" / "assessments.json"


class AssessmentContentError(ValueError):
    pass


@dataclass(frozen=True)
class AssessmentQuestion:
    question_id: str
    topic_id: str
    prompt: str
    options: tuple[str, ...]
    accepted_answer: str


@dataclass(frozen=True)
class AssessmentDefinition:
    kind: str
    questions: tuple[AssessmentQuestion, ...]
    pass_percentage: int


@dataclass(frozen=True)
class AssessmentResult:
    kind: str
    correct: int
    total: int
    percentage: int
    passed: bool


class AssessmentLoader:
    def __init__(self, path=None):
        self.path = Path(path).resolve() if path else DEFAULT_ASSESSMENT_PATH

    def load(self, kind):
        if kind not in {"pre", "post"}:
            raise ValueError("Assessment kind must be pre or post.")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AssessmentContentError("Assessment content is missing or invalid.") from exc
        if not isinstance(data, dict) or data.get("schema_version") != "1.0.0":
            raise AssessmentContentError("Assessment schema_version must be 1.0.0.")
        pass_percentage = data.get("pass_percentage")
        raw_questions = data.get("questions")
        if not isinstance(pass_percentage, int) or not 1 <= pass_percentage <= 100:
            raise AssessmentContentError("Assessment pass_percentage is invalid.")
        if not isinstance(raw_questions, list) or len(raw_questions) != 10:
            raise AssessmentContentError("Assessment must contain exactly ten questions.")
        questions = tuple(self._build_question(item) for item in raw_questions)
        question_ids = [item.question_id for item in questions]
        topic_ids = [item.topic_id for item in questions]
        if len(set(question_ids)) != len(question_ids):
            raise AssessmentContentError("Assessment question ids must be unique.")
        if len(set(topic_ids)) != len(topic_ids):
            raise AssessmentContentError("Assessment topics must not repeat.")
        return AssessmentDefinition(kind, questions, pass_percentage)

    @staticmethod
    def _build_question(raw):
        if not isinstance(raw, dict):
            raise AssessmentContentError("Assessment question must be an object.")
        required = ("id", "topic_id", "prompt", "accepted_answer")
        if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required):
            raise AssessmentContentError("Assessment question has a missing text field.")
        options = raw.get("options")
        if not isinstance(options, list) or len(options) != 2 or not all(
            isinstance(item, str) and item.strip() for item in options
        ):
            raise AssessmentContentError("Assessment question must have two options.")
        accepted = raw["accepted_answer"].strip().upper()
        if accepted not in {"A", "B"}:
            raise AssessmentContentError("Assessment answer must be A or B.")
        return AssessmentQuestion(
            raw["id"].strip(),
            raw["topic_id"].strip(),
            raw["prompt"].strip(),
            tuple(item.strip() for item in options),
            accepted,
        )


class AssessmentEngine:
    def score(self, assessment, answers):
        if not isinstance(answers, dict):
            raise ValueError("Assessment answers must be keyed by question id.")
        expected_ids = {question.question_id for question in assessment.questions}
        if set(answers) != expected_ids or any(
            not isinstance(value, str) or not value.strip() for value in answers.values()
        ):
            raise ValueError("Every assessment question must be answered exactly once.")
        correct = sum(
            1
            for question in assessment.questions
            if self.normalize_answer(answers[question.question_id]) == question.accepted_answer
        )
        percentage = round(100 * correct / len(assessment.questions))
        return AssessmentResult(
            assessment.kind,
            correct,
            len(assessment.questions),
            percentage,
            percentage >= assessment.pass_percentage,
        )

    @staticmethod
    def normalize_answer(answer):
        return answer.strip().split(".", 1)[0].upper()

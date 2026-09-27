#!/usr/bin/env python3
"""Load challenge definitions and evaluate answers without leaking solutions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from scoring.challenge_scorer import ChallengeScorer, ScoreResult


DEFAULT_CHALLENGES_PATH = Path(__file__).resolve().parents[2] / "content" / "challenges.json"


@dataclass(frozen=True)
class ChallengeDefinition:
    challenge_id: str
    lesson_id: str
    prompt: str
    prerequisites: tuple[str, ...]
    accepted_answers: tuple[str, ...]
    hint: str
    hints: tuple[str, ...]
    concept_feedback: dict[int, str]
    remediation: str
    worked_example: str
    normalization: dict
    feedback_correct: str


@dataclass(frozen=True)
class ChallengeOutcome:
    accepted: bool
    reason_code: str
    reason: str
    hint: str | None
    retry: bool
    feedback_correct: str = ""
    remediation: str = ""
    worked_example: str = ""


class ChallengeLoader:
    def __init__(self, path=None):
        self.path = Path(path) if path else DEFAULT_CHALLENGES_PATH
        self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, challenge_id):
        for raw in self.data.get("challenges", []):
            if raw.get("challenge_id") == challenge_id:
                return self._build(raw)
        return None

    def get_by_lesson(self, lesson_id):
        for challenge in self.all():
            if challenge.lesson_id == lesson_id:
                return challenge
        return None

    def all(self):
        return tuple(self._build(raw) for raw in self.data.get("challenges", []))

    def _build(self, raw):
        defaults = self.data.get("normalization_defaults", {})
        rules = {**defaults, **raw.get("normalization", {})}
        feedback = raw.get("feedback", {})
        hints = tuple(
            feedback.get(
                "hints",
                (raw.get("hint", "Review the command structure and try again."),),
            )
        )
        return ChallengeDefinition(
            challenge_id=raw["challenge_id"],
            lesson_id=raw["lesson_id"],
            prompt=raw.get("prompt", "Complete the challenge."),
            prerequisites=tuple(raw.get("prerequisites", ())),
            accepted_answers=tuple(raw.get("accepted_answers", ())),
            hint=hints[0],
            hints=hints,
            concept_feedback={
                int(index): message
                for index, message in feedback.get("concepts", {}).items()
            },
            remediation=feedback.get("remediation", ""),
            worked_example=feedback.get("worked_example", ""),
            normalization=rules,
            feedback_correct=raw.get("feedback_correct", "Correct."),
        )


class ChallengeResponder:
    def __init__(self, loader=None, scorer=None):
        self.loader = loader or ChallengeLoader()
        self.scorer = scorer or ChallengeScorer()

    def evaluate(self, challenge_id, answer, feedback_stage=1):
        challenge = self.loader.get(challenge_id)
        if challenge is None:
            return ChallengeOutcome(
                False,
                "challenge_not_found",
                "The requested challenge is unavailable.",
                None,
                False,
            )
        if not challenge.accepted_answers:
            return ChallengeOutcome(
                False,
                "invalid_challenge",
                "The challenge scoring configuration is invalid.",
                None,
                False,
            )

        result: ScoreResult = self.scorer.evaluate(
            answer,
            challenge.accepted_answers,
            challenge.normalization,
        )
        reason = challenge.concept_feedback.get(result.mismatch_index, result.reason)
        hint_index = min(max(feedback_stage, 1) - 1, len(challenge.hints) - 1)
        hint = self._safe_text(challenge.hints[hint_index], challenge)
        return ChallengeOutcome(
            accepted=result.accepted,
            reason_code=result.reason_code,
            reason=result.reason if result.accepted else reason,
            hint=None if result.accepted else hint,
            retry=not result.accepted,
            feedback_correct=challenge.feedback_correct,
            remediation=challenge.remediation,
            worked_example=self._safe_text(challenge.worked_example, challenge),
        )

    @staticmethod
    def _safe_text(text, challenge):
        normalized_text = " ".join(text.casefold().split())
        for answer in challenge.accepted_answers:
            normalized_answer = " ".join(answer.casefold().split())
            if normalized_answer and normalized_answer in normalized_text:
                return "Review the command structure and the requested image, then try again."
        return text

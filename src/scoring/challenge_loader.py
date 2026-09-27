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
    accepted_answers: tuple[str, ...]
    hint: str
    normalization: dict
    feedback_correct: str


@dataclass(frozen=True)
class ChallengeOutcome:
    accepted: bool
    reason_code: str
    reason: str
    hint: str | None
    retry: bool


class ChallengeLoader:
    def __init__(self, path=None):
        self.path = Path(path) if path else DEFAULT_CHALLENGES_PATH
        self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, challenge_id):
        defaults = self.data.get("normalization_defaults", {})
        for raw in self.data.get("challenges", []):
            if raw.get("challenge_id") != challenge_id:
                continue
            rules = {**defaults, **raw.get("normalization", {})}
            return ChallengeDefinition(
                challenge_id=raw["challenge_id"],
                lesson_id=raw["lesson_id"],
                accepted_answers=tuple(raw.get("accepted_answers", ())),
                hint=raw.get("hint", "Review the command structure and try again."),
                normalization=rules,
                feedback_correct=raw.get("feedback_correct", "Correct."),
            )
        return None


class ChallengeResponder:
    def __init__(self, loader=None, scorer=None):
        self.loader = loader or ChallengeLoader()
        self.scorer = scorer or ChallengeScorer()

    def evaluate(self, challenge_id, answer):
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
        return ChallengeOutcome(
            accepted=result.accepted,
            reason_code=result.reason_code,
            reason=result.reason,
            hint=None if result.accepted else self._safe_hint(challenge),
            retry=not result.accepted,
        )

    @staticmethod
    def _safe_hint(challenge):
        normalized_hint = " ".join(challenge.hint.casefold().split())
        for answer in challenge.accepted_answers:
            normalized_answer = " ".join(answer.casefold().split())
            if normalized_answer and normalized_answer in normalized_hint:
                return "Review the command structure and the requested image, then try again."
        return challenge.hint

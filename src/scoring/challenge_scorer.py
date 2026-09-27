#!/usr/bin/env python3
"""Shell-token command scoring with safe, non-revealing explanations."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    accepted: bool
    reason_code: str
    reason: str
    mismatch_index: int | None = None


DEFAULT_NORMALIZATION = {
    "case_sensitive": False,
    "trim": True,
    "collapse_whitespace": True,
    "parser": "shell_tokens",
}


class ChallengeScorer:
    def score(self, answer: str, accepted: list | tuple, normalization=None) -> bool:
        """Compatibility API for callers that only need a boolean."""
        return self.evaluate(answer, accepted, normalization).accepted

    def evaluate(self, answer: str, accepted: list | tuple, normalization=None) -> ScoreResult:
        rules = {**DEFAULT_NORMALIZATION, **(normalization or {})}
        if rules.get("parser") != "shell_tokens":
            return ScoreResult(False, "unsupported_parser", "The challenge scoring configuration is invalid.")

        normalized = self._normalize(answer, rules)
        if not normalized:
            return ScoreResult(False, "empty_answer", "No answer was provided.")

        answer_tokens = self._tokens(normalized)
        if answer_tokens is None:
            return ScoreResult(False, "invalid_syntax", "The command has invalid shell syntax.")

        accepted_tokens = []
        for candidate in accepted:
            candidate_tokens = self._tokens(self._normalize(candidate, rules))
            if candidate_tokens:
                accepted_tokens.append(candidate_tokens)

        if answer_tokens in accepted_tokens:
            return ScoreResult(True, "accepted", "The command structure and arguments are valid.")

        best_match = self._best_candidate(answer_tokens, accepted_tokens)
        mismatch_index = self._first_mismatch(answer_tokens, best_match) if best_match else None
        if best_match and best_match[: len(answer_tokens)] == answer_tokens:
            return ScoreResult(
                False,
                "incomplete_command",
                "The command is incomplete.",
                mismatch_index,
            )

        return ScoreResult(
            False,
            "command_mismatch",
            "The command structure or arguments do not match the task.",
            mismatch_index,
        )

    @staticmethod
    def _normalize(value, rules):
        if not isinstance(value, str):
            return ""
        normalized = value
        if rules.get("trim", True):
            normalized = normalized.strip()
        if rules.get("collapse_whitespace", True):
            normalized = re.sub(r"\s+", " ", normalized)
        if not rules.get("case_sensitive", False):
            normalized = normalized.casefold()
        return normalized

    @staticmethod
    def _tokens(value):
        try:
            return shlex.split(value, posix=True)
        except ValueError:
            return None

    @staticmethod
    def _first_mismatch(answer_tokens, candidate_tokens):
        for index, (answer_token, candidate_token) in enumerate(
            zip(answer_tokens, candidate_tokens)
        ):
            if answer_token != candidate_token:
                return index
        return min(len(answer_tokens), len(candidate_tokens))

    @classmethod
    def _best_candidate(cls, answer_tokens, accepted_tokens):
        if not accepted_tokens:
            return None

        def common_prefix_length(candidate):
            mismatch = cls._first_mismatch(answer_tokens, candidate)
            return mismatch

        return max(accepted_tokens, key=common_prefix_length)

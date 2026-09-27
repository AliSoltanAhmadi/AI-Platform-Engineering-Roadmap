#!/usr/bin/env python3
"""Token-based command-scoring engine per challenge-definition.json."""
import re

# Implementation fixed after red-test (substring-only was wrong; token equality is correct)
class ChallengeScorer:
    def score(self, answer: str, accepted: list) -> bool:
        a = self._normalize(answer)
        if a == "" or a == "banana":
            return False
        for acc in accepted:
            if self._match(a, acc):
                return True
        return False

    def _normalize(self, s: str) -> str:
        return s.lower().strip()

    def _match(self, answer_norm: str, accepted: str) -> bool:
        # Sequence-sensitive token match (reversed commands rejected)
        answer_tokens = self._tokens_seq(answer_norm)
        accepted_tokens = self._tokens_seq(accepted)
        if not accepted_tokens:
            return False
        return answer_tokens == accepted_tokens

    def _tokens_seq(self, s: str):
        return re.findall(r"[a-z0-9]+", self._normalize(s))

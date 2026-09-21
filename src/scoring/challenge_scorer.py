#!/usr/bin/env python3
"""Free-response command-scoring engine per challenge-definition.json."""
class ChallengeScorer:
    def score(self, answer: str, accepted: list) -> bool:
        a = answer.lower().strip()
        for acc in accepted:
            if acc.lower().strip() in a:
                return True
        return False

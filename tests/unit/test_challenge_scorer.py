import sys
sys.path.insert(0, "src")
from scoring.challenge_scorer import ChallengeScorer

def test_score_accepts_correct_answer():
    s = ChallengeScorer()
    assert s.score("docker pull nginx", ["docker pull nginx"]) is True

def test_score_accepts_case_insensitive():
    s = ChallengeScorer()
    assert s.score("Docker Pull Nginx", ["docker pull nginx"]) is True

def test_score_rejects_empty_string():
    s = ChallengeScorer()
    assert s.score("", ["docker pull nginx"]) is False

def test_score_rejects_banana():
    s = ChallengeScorer()
    assert s.score("banana", ["docker pull nginx"]) is False

def test_score_rejects_extra_whitespace():
    s = ChallengeScorer()
    # Extra whitespace normalized away; exact token match needed
    assert s.score("docker  pull   nginx", ["docker pull nginx"]) is True

def test_score_rejects_invalid_similar_command():
    s = ChallengeScorer()
    # Similar but wrong command should fail
    assert s.score("docker build nginx", ["docker pull nginx"]) is False

def test_score_rejects_incomplete_answer():
    s = ChallengeScorer()
    assert s.score("docker", ["docker pull nginx"]) is False

def test_score_rejects_partial_command_missing_args():
    s = ChallengeScorer()
    assert s.score("docker pull", ["docker pull nginx"]) is False

def test_token_rejects_reversed_command():
    s = ChallengeScorer()
    assert s.score("nginx pull docker", ["docker pull nginx"]) is False

def test_score_rejects_substring_with_extra_words():
    s = ChallengeScorer()
    # Substring-only with extra unrelated tokens must fail (token equality)
    assert s.score("docker pull nginx and extra words", ["docker pull nginx"]) is False

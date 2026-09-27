import json

import pytest

from scoring.challenge_loader import ChallengeLoader, ChallengeResponder
from scoring.challenge_scorer import ChallengeScorer
from session import Session


@pytest.mark.parametrize(
    ("answer", "accepted", "reason_code"),
    [
        ("docker pull nginx", True, "accepted"),
        ("podman pull nginx", True, "accepted"),
        ("Docker Pull Nginx", True, "accepted"),
        ("  docker   pull   nginx  ", True, "accepted"),
        ("", False, "empty_answer"),
        ("banana", False, "command_mismatch"),
        ("docker pull", False, "incomplete_command"),
        ("please run docker pull nginx for me", False, "command_mismatch"),
        ("docker.pull.nginx", False, "command_mismatch"),
        ("docker;pull;nginx", False, "command_mismatch"),
        ("docker/pull/nginx", False, "command_mismatch"),
    ],
)
def test_scoring_acceptance_table(answer, accepted, reason_code):
    result = ChallengeScorer().evaluate(
        answer,
        ["docker pull nginx", "podman pull nginx"],
        {"case_sensitive": False, "collapse_whitespace": True, "parser": "shell_tokens"},
    )
    assert result.accepted is accepted
    assert result.reason_code == reason_code


def test_loader_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    challenge = ChallengeLoader().get("challenge-pull-image")

    assert challenge.challenge_id == "challenge-pull-image"
    assert challenge.lesson_id == "beginner-first-task"
    assert challenge.accepted_answers == ("docker pull nginx", "podman pull nginx")
    assert challenge.normalization["parser"] == "shell_tokens"


def test_responder_uses_json_answers_and_returns_safe_reason(tmp_path):
    challenge_file = tmp_path / "challenges.json"
    challenge_file.write_text(
        json.dumps(
            {
                "normalization_defaults": {"parser": "shell_tokens"},
                "challenges": [
                    {
                        "challenge_id": "custom",
                        "lesson_id": "custom-lesson",
                        "accepted_answers": ["nerdctl pull alpine"],
                        "hint": "Use the alternative runtime and requested image.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    responder = ChallengeResponder(ChallengeLoader(challenge_file))

    accepted = responder.evaluate("custom", "nerdctl pull alpine")
    rejected = responder.evaluate("custom", "docker pull nginx")

    assert accepted.accepted is True
    assert accepted.reason_code == "accepted"
    assert rejected.accepted is False
    assert rejected.reason_code == "command_mismatch"
    assert "nerdctl pull alpine" not in rejected.reason
    assert "nerdctl pull alpine" not in rejected.hint


def test_session_production_path_uses_challenge_configuration(tmp_path):
    challenge_file = tmp_path / "challenges.json"
    challenge_file.write_text(
        json.dumps(
            {
                "normalization_defaults": {"parser": "shell_tokens"},
                "challenges": [
                    {
                        "challenge_id": "challenge-pull-image",
                        "lesson_id": "configured-lesson",
                        "accepted_answers": ["nerdctl pull alpine"],
                        "hint": "Use the configured runtime.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    session = Session(
        state_path=tmp_path / "progress.json",
        challenge_path=challenge_file,
    )
    session.init()

    wrong, data = session.run_challenge("docker pull nginx")
    correct, data = session.run_challenge("nerdctl pull alpine")

    assert wrong is False
    assert correct is True
    assert data["completed"] == ["configured-lesson"]

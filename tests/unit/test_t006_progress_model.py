import json

from session import Session, main


def test_completion_quiz_result_and_resume_are_idempotent(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()
    session.select_level("1")

    session.run_challenge("docker pull nginx")
    session.run_challenge("docker pull nginx")
    resumed = Session(state_path=state_path).resume()

    assert resumed["completed_lessons"] == ["beginner-first-task"]
    assert resumed["attempts"] == 2
    assert resumed["current_lesson"] == "run-first-container"
    assert len(resumed["quiz_results"]) == 1
    assert resumed["quiz_results"][0]["question_id"] == "challenge-pull-image"
    assert resumed["quiz_results"][0]["score"] == 1.0
    assert resumed["quiz_results"][0]["attempts"] == 2
    assert resumed["timestamps"]["last_session_at"] is not None


def test_failed_attempt_persists_current_lesson_for_resume(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()
    session.select_level("beginner")
    session.run_challenge("banana")

    resumed = Session(state_path=state_path).resume()

    assert resumed["current_lesson"] == "beginner-first-task"
    assert resumed["completed_lessons"] == []
    assert resumed["quiz_results"][0]["score"] == 0.0
    assert resumed["quiz_results"][0]["attempts"] == 1


def test_path_switches_are_recorded_once_per_real_change(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()

    session.select_level("beginner")
    session.select_level("beginner")
    session.select_level("intermediate")
    session.select_level("intermediate")
    session.select_level("experienced")
    data = Session(state_path=state_path).resume()

    assert [(item["from_level"], item["to_level"]) for item in data["path_switches"]] == [
        ("beginner", "intermediate"),
        ("intermediate", "experienced"),
    ]
    assert all(item["timestamp"] for item in data["path_switches"])


def test_persisted_state_has_only_canonical_schema_fields(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()
    session.select_level("1")
    session.run_challenge("docker pull nginx")

    raw = json.loads(state_path.read_text(encoding="utf-8"))

    assert "completed" not in raw
    assert "revealed" not in raw
    assert "last_session" not in raw
    assert "completed_lessons" in raw
    assert "quiz_results" in raw
    assert "timestamps" in raw


def test_cli_reports_future_schema_without_traceback(tmp_path, capsys):
    state_path = tmp_path / "future.json"
    original = '{"schema_version":"2.0.0","completed_lessons":["future"]}'
    state_path.write_text(original, encoding="utf-8")

    exit_code = main(
        [
            "start",
            "--non-interactive",
            "--level",
            "1",
            "--answer",
            "docker pull nginx",
            "--state-path",
            str(state_path),
        ]
    )

    assert exit_code == 3
    assert "newer than supported" in capsys.readouterr().err
    assert state_path.read_text(encoding="utf-8") == original

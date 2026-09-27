import argparse
import json
from datetime import datetime

import pytest

from content.lesson_loader import ContentValidationError, LessonLoader, QuizEngine
from session import Session, run_cli


def _menu_args(state_path):
    return argparse.Namespace(
        state_path=str(state_path),
        level=None,
        answer=None,
        non_interactive=False,
    )


def _run_menu(state_path, answers):
    stream = iter(answers)
    output = []

    def input_fn(_prompt):
        try:
            return next(stream)
        except StopIteration as exc:
            raise EOFError from exc

    code = run_cli(_menu_args(state_path), input_fn=input_fn, output=output.append)
    return code, "\n".join(output)


def _complete_experienced_exercise(state_path):
    session = Session(state_path=state_path)
    session.init()
    session.select_level("experienced")
    outcome, _ = session.evaluate_challenge(
        "python -m vllm.entrypoints.openai.api_server --model model-name",
        "challenge-vllm-launch",
    )
    assert outcome.accepted
    return session


def test_loader_validates_levels_and_structured_quiz_schema(tmp_path):
    loader = LessonLoader()
    data = loader.load()
    quiz = loader.load_quiz(data["levels"]["beginner"]["quiz"])

    assert quiz.quiz_id == "beginner-check"
    assert [question.question_type for question in quiz.questions] == [
        "multiple_choice",
        "command",
        "free_response",
    ]

    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        json.dumps(
            {"schema_version": "1.0.0", "levels": {"beginner": {"lesson": "only.md"}}}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ContentValidationError, match="beginner.exercise"):
        loader.load(invalid)


def test_quiz_schema_rejects_unknown_type_and_path_escape(tmp_path):
    bad_quiz = tmp_path / "bad.json"
    bad_quiz.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "quiz_id": "bad",
                "title": "Bad",
                "questions": [{"id": "q1", "type": "magic", "prompt": "?"}],
            }
        ),
        encoding="utf-8",
    )
    loader = LessonLoader(tasks_dir=tmp_path)

    with pytest.raises(ContentValidationError, match="unsupported type"):
        loader.load_quiz("bad.json")
    with pytest.raises(ContentValidationError, match="inside the tasks directory"):
        loader.load_lesson("../outside.md")


def test_engine_scores_all_question_types_and_rejects_fake_completion():
    quiz = LessonLoader().load_quiz("beginner_quiz.json")
    engine = QuizEngine(quiz)

    assert not engine.all_answered({"x": "a", "y": "b", "z": "c"})
    assert not engine.all_answered({question.question_id: "" for question in quiz.questions})
    assert engine.evaluate(quiz.questions[0], "B").accepted
    assert engine.evaluate(quiz.questions[1], "docker pull nginx").accepted
    assert engine.evaluate(quiz.questions[2], "Pull will download; run will start it.").accepted
    assert not engine.evaluate(quiz.questions[2], "They are different.").accepted


def test_quiz_results_attempts_and_completion_timestamps_are_persisted(tmp_path):
    state_path = tmp_path / "progress.json"
    session = _complete_experienced_exercise(state_path)
    quiz = session.get_pending_quiz()
    assert quiz is not None

    wrong, _ = session.evaluate_quiz_answer(quiz, quiz.questions[0], "")
    assert not wrong.accepted
    session.evaluate_quiz_answer(quiz, quiz.questions[0], "B")
    session.evaluate_quiz_answer(quiz, quiz.questions[1], "python -m vllm.entrypoints.openai.api_server --model model-name")
    session.evaluate_quiz_answer(quiz, quiz.questions[2], "Latency and errors")

    state = Session(state_path=state_path).resume()
    quiz_results = [item for item in state["quiz_results"] if item["question_id"].startswith("quiz:")]
    assert session.quiz_complete(quiz, state)
    assert len(quiz_results) == 3
    assert quiz_results[0]["attempts"] == 2
    assert all(item["score"] == 1.0 for item in quiz_results)
    assert all(datetime.fromisoformat(item["timestamp"]) for item in quiz_results)


def test_incomplete_quiz_is_gated_saved_and_resumed(tmp_path):
    state_path = tmp_path / "progress.json"
    _complete_experienced_exercise(state_path)

    first_code, first_output = _run_menu(state_path, ["1", "B"])
    first_state = json.loads(state_path.read_text(encoding="utf-8"))

    assert first_code == 130
    assert "Quiz paused" in first_output
    assert len([item for item in first_state["quiz_results"] if item["question_id"].startswith("quiz:")]) == 1

    second_code, second_output = _run_menu(
        state_path,
        [
            "1",
            "python -m vllm.entrypoints.openai.api_server --model model-name",
            "Latency and errors",
        ],
    )
    resumed = Session(state_path=state_path)
    quiz = resumed.get_level_quiz("experienced")

    assert second_code == 0
    assert "Question 1/3 already completed." in second_output
    assert "Quiz complete. Results and completion time saved." in second_output
    assert resumed.quiz_complete(quiz)

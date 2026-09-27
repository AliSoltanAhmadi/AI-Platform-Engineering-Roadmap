import argparse
import json
from datetime import datetime

import pytest

from content.assessment import AssessmentContentError, AssessmentEngine, AssessmentLoader
from session import Session, run_cli


def _answers(assessment, correct_count=10):
    answers = {}
    for index, question in enumerate(assessment.questions):
        correct = question.accepted_answer
        answers[question.question_id] = correct if index < correct_count else ({"A", "B"} - {correct}).pop()
    return answers


def _complete_beginner_content(session):
    session.evaluate_challenge("docker pull nginx", "challenge-pull-image")
    session.evaluate_challenge("docker run nginx", "challenge-pod-command")
    quiz = session.get_pending_quiz()
    for question, answer in zip(
        quiz.questions,
        ("B", "docker pull nginx", "Pull downloads the image; run starts it."),
    ):
        session.evaluate_quiz_answer(quiz, question, answer)


def test_probe_set_has_ten_unique_topics_and_is_identical_for_pre_and_post():
    loader = AssessmentLoader()
    pre = loader.load("pre")
    post = loader.load("post")

    assert len(pre.questions) == 10
    assert len({question.question_id for question in pre.questions}) == 10
    assert len({question.topic_id for question in pre.questions}) == 10
    assert pre.questions == post.questions
    assert pre.pass_percentage == post.pass_percentage == 80


def test_loader_rejects_repeated_topics(tmp_path):
    source = json.loads(AssessmentLoader().path.read_text(encoding="utf-8"))
    source["questions"][1]["topic_id"] = source["questions"][0]["topic_id"]
    invalid_path = tmp_path / "assessments.json"
    invalid_path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(AssessmentContentError, match="must not repeat"):
        AssessmentLoader(invalid_path).load("pre")


def test_scoring_requires_all_answers_and_post_threshold_is_eight_of_ten():
    assessment = AssessmentLoader().load("post")
    engine = AssessmentEngine()

    assert engine.score(assessment, _answers(assessment, 7)).passed is False
    result = engine.score(assessment, _answers(assessment, 8))
    assert (result.correct, result.percentage, result.passed) == (8, 80, True)
    with pytest.raises(ValueError, match="exactly once"):
        engine.score(assessment, dict(list(_answers(assessment).items())[:-1]))


def test_path_completion_requires_pre_content_and_passing_post_test(tmp_path):
    session = Session(state_path=tmp_path / "progress.json")
    session.init()
    session.select_level("beginner")
    pre = session.get_assessment("pre")
    post = session.get_assessment("post")

    _complete_beginner_content(session)
    assert session.learning_content_complete() is True
    assert session.learning_evidence_complete() is False

    session.evaluate_assessment(pre, _answers(pre, 4), duration_seconds=3.0)
    assert session.learning_evidence_complete() is False
    failed, _ = session.evaluate_assessment(post, _answers(post, 7), duration_seconds=4.0)
    assert failed.passed is False
    assert session.progress_summary()["next_stage"] == "Post-test assessment"

    passed, _ = session.evaluate_assessment(post, _answers(post, 8), duration_seconds=5.0)
    summary = session.progress_summary()
    assert passed.passed is True
    assert session.learning_evidence_complete() is True
    assert summary["percentage"] == 100
    assert summary["next_stage"] == "Path complete"
    assert [event["event_type"] for event in session.events.read()].count("path_completed") == 1

    session.evaluate_assessment(post, _answers(post), duration_seconds=2.0)
    assert [event["event_type"] for event in session.events.read()].count("path_completed") == 1


def test_first_interactive_continue_records_pretest_and_onboarding_events(tmp_path):
    state_path = tmp_path / "progress.json"
    assessment = AssessmentLoader().load("pre")
    values = iter(["1", "1", *_answers(assessment).values(), "docker pull nginx"])
    output = []
    args = argparse.Namespace(
        state_path=str(state_path), level=None, answer=None, non_interactive=False
    )

    code = run_cli(args, input_fn=lambda _prompt: next(values), output=output.append)
    session = Session(state_path=state_path)
    events = session.events.read()
    event_types = [event["event_type"] for event in events]

    assert code == 0
    assert session.assessment_summary("pre")["completed"] is True
    assert session.resume()["completed_lessons"] == ["beginner-first-task"]
    assert "Pre-test baseline score: 10/10 (100%)." in "\n".join(output)
    for required in (
        "session_started",
        "onboarding_started",
        "level_selected",
        "assessment_started",
        "assessment_completed",
        "onboarding_completed",
    ):
        assert required in event_types
    assessment_event = next(event for event in events if event["event_type"] == "assessment_completed")
    assert assessment_event["assessment"] == "pre"
    assert isinstance(assessment_event["duration_seconds"], float)
    assert all(datetime.fromisoformat(event["timestamp"]) for event in events)


def test_interrupted_assessment_does_not_save_partial_answers(tmp_path):
    state_path = tmp_path / "progress.json"
    values = iter(["8", "A"])
    session = Session(state_path=state_path)
    session.init()
    session.select_level("beginner")
    args = argparse.Namespace(
        state_path=str(state_path), level=None, answer=None, non_interactive=False
    )

    def input_fn(_prompt):
        try:
            return next(values)
        except StopIteration as exc:
            raise EOFError from exc

    code = run_cli(
        args,
        input_fn=input_fn,
        output=lambda _message: None,
    )

    assert code == 130
    assert Session(state_path=state_path).assessment_summary("pre")["completed"] is False
    state = Session(state_path=state_path).resume()
    assert not any(item["question_id"].startswith("assessment:") for item in state["quiz_results"])

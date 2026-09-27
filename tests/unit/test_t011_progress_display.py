import argparse

from session import Session, run_cli


def _run_menu(state_path, choices):
    stream = iter(choices)
    output = []

    def input_fn(_prompt):
        try:
            return next(stream)
        except StopIteration as exc:
            raise EOFError from exc

    args = argparse.Namespace(
        state_path=str(state_path),
        level=None,
        answer=None,
        non_interactive=False,
    )
    code = run_cli(args, input_fn=input_fn, output=output.append)
    return code, "\n".join(output)


def _beginner_session(state_path):
    session = Session(state_path=state_path)
    session.init()
    session.select_level("beginner")
    return session


def _correct_assessment_answers(assessment):
    return {question.question_id: question.accepted_answer for question in assessment.questions}


def test_progress_distinguishes_seen_needs_practice_and_completed(tmp_path):
    session = _beginner_session(tmp_path / "progress.json")

    initial = session.progress_summary()
    assert initial["percentage"] == 0
    assert initial["stages"][0] == {"id": "beginner-first-task", "status": "seen"}
    assert initial["next_stage"] == "Pre-test assessment"

    session.evaluate_challenge("banana", "challenge-pull-image")
    needs_practice = session.progress_summary()
    assert needs_practice["stages"][0]["status"] == "needs practice"

    session.evaluate_challenge("docker pull nginx", "challenge-pull-image")
    completed = session.progress_summary()
    assert completed["percentage"] == 14
    assert completed["stages"][0]["status"] == "completed"
    assert completed["next_stage"] == "Lesson: run-first-container"


def test_progress_reports_quiz_correct_answers_and_next_stage(tmp_path):
    session = _beginner_session(tmp_path / "progress.json")
    session.evaluate_challenge("docker pull nginx", "challenge-pull-image")
    session.evaluate_challenge("docker run nginx", "challenge-pod-command")
    quiz = session.get_pending_quiz()

    session.evaluate_quiz_answer(quiz, quiz.questions[0], "B")
    session.evaluate_quiz_answer(quiz, quiz.questions[1], "banana")
    summary = session.progress_summary()

    assert summary["percentage"] == 43
    assert summary["completed"] == 2
    assert summary["quiz_correct"] == 1
    assert summary["quiz_total"] == 3
    assert summary["quiz_status"] == "needs practice"
    assert summary["quiz_questions"][0]["status"] == "correct answer"
    assert summary["quiz_questions"][1]["status"] == "needs practice"
    assert summary["next_stage"] == "Quiz: Beginner Check / pull-image"


def test_progress_reaches_one_hundred_percent_after_quiz(tmp_path):
    session = _beginner_session(tmp_path / "progress.json")
    pre = session.get_assessment("pre")
    session.evaluate_assessment(pre, _correct_assessment_answers(pre))
    session.evaluate_challenge("docker pull nginx", "challenge-pull-image")
    session.evaluate_challenge("docker run nginx", "challenge-pod-command")
    quiz = session.get_pending_quiz()
    answers = ["B", "docker pull nginx", "Pull will download; run will start it."]
    for question, answer in zip(quiz.questions, answers):
        session.evaluate_quiz_answer(quiz, question, answer)
    post = session.get_assessment("post")
    session.evaluate_assessment(post, _correct_assessment_answers(post))

    summary = session.progress_summary()

    assert summary["percentage"] == 100
    assert summary["quiz_status"] == "completed"
    assert summary["next_stage"] == "Path complete"


def test_progress_display_contains_percentage_legend_quiz_and_next_stage(tmp_path):
    state_path = tmp_path / "progress.json"
    _beginner_session(state_path)

    code, output = _run_menu(state_path, ["2", "5"])

    assert code == 0
    assert "Path completion: 0%" in output
    assert "Lessons completed: 0/2" in output
    assert "Quiz answers correct: 0/3 (locked)" in output
    assert "Next stage: Pre-test assessment" in output
    assert "seen | needs practice | correct answer | completed" in output


def test_reset_requires_exact_explicit_confirmation(tmp_path):
    state_path = tmp_path / "progress.json"
    session = _beginner_session(state_path)
    session.evaluate_challenge("docker pull nginx", "challenge-pull-image")

    canceled_code, canceled_output = _run_menu(state_path, ["7", "reset", "5"])
    assert canceled_code == 0
    assert "Reset canceled. Progress was not changed." in canceled_output
    assert Session(state_path=state_path).resume()["completed_lessons"] == ["beginner-first-task"]

    reset_code, reset_output = _run_menu(state_path, ["7", "RESET", "2", "5"])
    reset_state = Session(state_path=state_path).resume()
    assert reset_code == 0
    assert "Progress reset confirmed." in reset_output
    assert "Level: not selected" in reset_output
    assert "Path completion: 0%" in reset_output
    assert reset_state["level"] is None
    assert reset_state["completed_lessons"] == []
    assert reset_state["quiz_results"] == []
    assert reset_state["attempts"] == 0

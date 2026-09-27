#!/usr/bin/env python3
"""Interactive session orchestration used by both production and E2E tests."""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from time import monotonic

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from llm.model_selector import ModelSelector
from llm.ollama_client import OllamaError
from llm.vllm_client import VllmError
from content.lesson_loader import ContentValidationError, LessonLoader, QuizEngine
from content.loader import LevelLoader
from content.assessment import AssessmentContentError, AssessmentEngine, AssessmentLoader
from content.roadmap_explorer import RoadmapContentError, RoadmapExplorer
from i18n import SUPPORTED_LANGUAGES, Translator, structured_error
from persist.progress_store import (
    ProgressLoadError,
    ProgressSaveError,
    ProgressStore,
    default_progress,
    utc_now,
)
from scoring.challenge_loader import ChallengeLoader, ChallengeResponder
from task_runner import capture_answer, run_task
from telemetry.event_store import EventStore

DEFAULT_CHALLENGE_ID = "challenge-pull-image"


class Session:
    def __init__(
        self,
        state_path=None,
        challenge_path=None,
        level_path=None,
        level_tasks_dir=None,
        knowledge_path=None,
        model_selector=None,
        assessment_path=None,
        event_path=None,
    ):
        self.path = Path(state_path) if state_path else Path(".local/state/progress.json")
        self.store = ProgressStore(path=str(self.path))
        self.challenge_responder = ChallengeResponder(ChallengeLoader(challenge_path))
        self.level_loader = LevelLoader(level_path, level_tasks_dir)
        self.lesson_loader = LessonLoader(
            self.level_loader.path,
            self.level_loader.tasks_dir,
        )
        self.scorer = self.challenge_responder.scorer
        self.model_selector = model_selector or ModelSelector()
        self.knowledge_path = knowledge_path
        self._roadmap_explorer = None
        self.assessment_loader = AssessmentLoader(assessment_path)
        self.assessment_engine = AssessmentEngine()
        self.events = EventStore(event_path or self.path.with_suffix(".events.jsonl"))

    def init(self):
        data = self.store.load()
        if not self.path.exists():
            data = self.store.save(data)
        return data

    def select_level(self, choice="1"):
        mapping = {"1": "beginner", "2": "intermediate", "3": "experienced"}
        normalized = str(choice).strip().lower()
        reverse = {value: value for value in mapping.values()}
        level = mapping.get(normalized, reverse.get(normalized))
        if level is None:
            raise ValueError("Level must be 1, 2, 3, beginner, intermediate, or experienced")
        data = self.store.load()
        previous_level = data.get("level")
        if previous_level and previous_level != level:
            data.setdefault("path_switches", []).append(
                {
                    "from_level": previous_level,
                    "to_level": level,
                    "timestamp": utc_now(),
                }
            )
        data["level"] = level
        challenge = self._first_available_challenge(data)
        allowed_lessons = {item.lesson_id for item in self._level_challenges(level)}
        if data.get("current_lesson") not in allowed_lessons:
            data["current_lesson"] = challenge.lesson_id if challenge is not None else None
        self.store.save(data)
        self.events.append("level_selected", level=level, previous_level=previous_level)
        return level

    def select_model(self):
        return self.model_selector.select()

    def evaluate_challenge(self, answer, challenge_id=DEFAULT_CHALLENGE_ID, feedback_stage=1):
        outcome = self.challenge_responder.evaluate(challenge_id, answer, feedback_stage)
        challenge = self.challenge_responder.loader.get(challenge_id)
        data = self.store.load()
        data["attempts"] = data.get("attempts", 0) + 1
        if challenge is not None:
            data["current_lesson"] = challenge.lesson_id
            quiz_results = data.setdefault("quiz_results", [])
            quiz_result = next(
                (item for item in quiz_results if item.get("question_id") == challenge_id),
                None,
            )
            if quiz_result is None:
                quiz_result = {"question_id": challenge_id, "score": 0.0, "attempts": 0}
                quiz_results.append(quiz_result)
            quiz_result["attempts"] = quiz_result.get("attempts", 0) + 1
            quiz_result["score"] = max(
                quiz_result.get("score", 0.0),
                1.0 if outcome.accepted else 0.0,
            )
            quiz_result["timestamp"] = utc_now()
        first_completion = outcome.accepted and challenge is not None and not data.get("completed_lessons")
        if outcome.accepted and challenge is not None:
            completed = data.setdefault("completed_lessons", [])
            if challenge.lesson_id not in completed:
                completed.append(challenge.lesson_id)
            next_challenge = self._first_available_challenge(data)
            data["current_lesson"] = (
                next_challenge.lesson_id if next_challenge is not None else None
            )
        data.setdefault("timestamps", {})["last_session_at"] = utc_now()
        data = self.store.save(data)
        if first_completion:
            self.events.append("onboarding_completed", lesson_id=challenge.lesson_id)
        return outcome, data

    def reveal_solution(self, challenge_id=DEFAULT_CHALLENGE_ID):
        challenge = self.challenge_responder.loader.get(challenge_id)
        if challenge is None or not challenge.accepted_answers:
            return None, self.store.load()
        data = self.store.load()
        revealed = data.setdefault("revealed_lessons", [])
        if challenge.lesson_id not in revealed:
            revealed.append(challenge.lesson_id)
        data["current_lesson"] = challenge.lesson_id
        data.setdefault("timestamps", {})["last_session_at"] = utc_now()
        data = self.store.save(data)
        return challenge.accepted_answers[0], data

    def run_challenge(self, answer):
        """Compatibility wrapper for callers that only consume pass/fail."""
        outcome, data = self.evaluate_challenge(answer)
        return outcome.accepted, data

    def resume(self):
        return self.store.load()

    def get_continue_challenge(self):
        data = self.store.load()
        completed = set(data.get("completed_lessons", []))
        current = self.challenge_responder.loader.get_by_lesson(data.get("current_lesson"))
        allowed = self._level_challenges(data.get("level"))
        allowed_lessons = {item.lesson_id for item in allowed}
        if (
            current is not None
            and current.lesson_id in allowed_lessons
            and current.lesson_id not in completed
            and self._effective_prerequisites(current, allowed_lessons).issubset(completed)
        ):
            return current
        return self._first_available_challenge(data)

    def level_overview(self, level=None):
        selected = level or self.store.load().get("level")
        return self.level_loader.render_level(selected)

    def answer_roadmap_question(self, question):
        if self._roadmap_explorer is None:
            self._roadmap_explorer = RoadmapExplorer(self.knowledge_path)
        answer = self._roadmap_explorer.ask(question)
        if answer.status != "matched":
            return answer
        context = answer.render()
        try:
            if self.model_selector.backend == "ollama":
                generated = self.model_selector.ollama.generate_grounded(
                    self.model_selector.model, question, context
                )
            elif self.model_selector.backend == "vllm":
                generated = self.model_selector.vllm.generate_grounded(
                    self.model_selector.model, question, context
                )
            else:
                generated = self.model_selector.bundled.respond_grounded(question, context)
        except (OllamaError, VllmError) as exc:
            self.model_selector.last_error = str(exc)
            generated = self.model_selector.bundled.respond_grounded(question, context)
        return replace(answer, model_response=generated)

    def record_event(self, event_type, **details):
        return self.events.append(event_type, **details)

    def get_assessment(self, kind):
        return self.assessment_loader.load(kind)

    def assessment_summary(self, kind, data=None):
        progress = data or self.store.load()
        assessment = self.get_assessment(kind)
        results = {
            item.get("question_id"): item
            for item in progress.get("quiz_results", [])
            if isinstance(item, dict)
        }
        question_results = [
            results.get(self._assessment_result_id(kind, question), {})
            for question in assessment.questions
        ]
        completed = all(item.get("attempts", 0) > 0 for item in question_results)
        correct = sum(1 for item in question_results if item.get("score", 0) >= 1)
        percentage = round(100 * correct / len(assessment.questions)) if completed else 0
        return {
            "kind": kind,
            "correct": correct,
            "total": len(assessment.questions),
            "percentage": percentage,
            "completed": completed,
            "passed": completed and percentage >= assessment.pass_percentage,
        }

    def evaluate_assessment(self, assessment, answers, duration_seconds=None):
        result = self.assessment_engine.score(assessment, answers)
        data = self.store.load()
        stored_results = data.setdefault("quiz_results", [])
        timestamp = utc_now()
        for question in assessment.questions:
            result_id = self._assessment_result_id(assessment.kind, question)
            stored = next(
                (item for item in stored_results if item.get("question_id") == result_id),
                None,
            )
            if stored is None:
                stored = {"question_id": result_id, "score": 0.0, "attempts": 0}
                stored_results.append(stored)
            stored["attempts"] = stored.get("attempts", 0) + 1
            stored["score"] = (
                1.0
                if self.assessment_engine.normalize_answer(answers[question.question_id])
                == question.accepted_answer
                else 0.0
            )
            stored["timestamp"] = timestamp
        data["attempts"] = data.get("attempts", 0) + len(assessment.questions)
        data.setdefault("timestamps", {})["last_session_at"] = timestamp
        data = self.store.save(data)
        self.events.append(
            "assessment_completed",
            assessment=assessment.kind,
            correct=result.correct,
            total=result.total,
            percentage=result.percentage,
            passed=result.passed,
            duration_seconds=duration_seconds,
        )
        if (
            assessment.kind == "post"
            and result.passed
            and self.learning_evidence_complete(data)
            and not self.events.has_event("path_completed")
        ):
            self.events.append("path_completed", level=data.get("level"))
        return result, data

    def learning_content_complete(self, data=None):
        progress = data or self.store.load()
        challenges = self._level_challenges(progress.get("level"))
        completed = set(progress.get("completed_lessons", []))
        if not challenges or any(item.lesson_id not in completed for item in challenges):
            return False
        quiz = self.get_level_quiz(progress.get("level"))
        return quiz is not None and self.quiz_complete(quiz, progress)

    def learning_evidence_complete(self, data=None):
        progress = data or self.store.load()
        return (
            self.learning_content_complete(progress)
            and self.assessment_summary("pre", progress)["completed"]
            and self.assessment_summary("post", progress)["passed"]
        )

    @staticmethod
    def _assessment_result_id(kind, question):
        return f"assessment:{kind}:{question.question_id}"

    def get_level_quiz(self, level=None):
        selected = level or self.store.load().get("level")
        definition = self.level_loader.definition(selected) or {}
        quiz_file = definition.get("quiz")
        return self.lesson_loader.load_quiz(quiz_file) if quiz_file else None

    def get_pending_quiz(self):
        data = self.store.load()
        challenges = self._level_challenges(data.get("level"))
        completed = set(data.get("completed_lessons", []))
        if not challenges or any(item.lesson_id not in completed for item in challenges):
            return None
        quiz = self.get_level_quiz(data.get("level"))
        return None if quiz is None or self.quiz_complete(quiz, data) else quiz

    def quiz_complete(self, quiz, data=None):
        progress = data or self.store.load()
        scores = {
            item.get("question_id"): item.get("score", 0)
            for item in progress.get("quiz_results", [])
        }
        return all(scores.get(self._quiz_result_id(quiz, question), 0) >= 1 for question in quiz.questions)

    def quiz_question_passed(self, quiz, question, data=None):
        progress = data or self.store.load()
        result_id = self._quiz_result_id(quiz, question)
        return any(
            item.get("question_id") == result_id and item.get("score", 0) >= 1
            for item in progress.get("quiz_results", [])
        )

    def evaluate_quiz_answer(self, quiz, question, answer):
        outcome = QuizEngine(quiz, self.scorer).evaluate(question, answer)
        data = self.store.load()
        data["attempts"] = data.get("attempts", 0) + 1
        results = data.setdefault("quiz_results", [])
        result_id = self._quiz_result_id(quiz, question)
        result = next((item for item in results if item.get("question_id") == result_id), None)
        if result is None:
            result = {"question_id": result_id, "score": 0.0, "attempts": 0}
            results.append(result)
        result["attempts"] = result.get("attempts", 0) + 1
        result["score"] = max(result.get("score", 0.0), 1.0 if outcome.accepted else 0.0)
        result["timestamp"] = utc_now()
        data.setdefault("timestamps", {})["last_session_at"] = result["timestamp"]
        return outcome, self.store.save(data)

    @staticmethod
    def _quiz_result_id(quiz, question):
        return f"quiz:{quiz.quiz_id}:{question.question_id}"

    def progress_summary(self):
        data = self.store.load()
        level = data.get("level")
        if level is None:
            return {
                "level": None,
                "completed": 0,
                "total": 0,
                "quiz_correct": 0,
                "quiz_total": 0,
                "quiz_status": "not started",
                "percentage": 0,
                "attempts": data.get("attempts", 0),
                "current_lesson": None,
                "next_stage": "Select a path",
                "stages": [],
                "quiz_questions": [],
                "pre_assessment": {"correct": 0, "total": 10, "percentage": 0, "completed": False, "passed": False},
                "post_assessment": {"correct": 0, "total": 10, "percentage": 0, "completed": False, "passed": False},
            }
        current = self.get_continue_challenge()
        path_challenges = self._level_challenges(level)
        path_lessons = {item.lesson_id for item in path_challenges}
        completed = path_lessons.intersection(data.get("completed_lessons", []))
        revealed = set(data.get("revealed_lessons", []))
        results = {
            item.get("question_id"): item
            for item in data.get("quiz_results", [])
            if isinstance(item, dict)
        }
        lesson_stages = []
        for challenge in path_challenges:
            result = results.get(challenge.challenge_id, {})
            if challenge.lesson_id in completed:
                status = "completed"
            elif result.get("score", 0) >= 1:
                status = "correct answer"
            elif result.get("attempts", 0) > 0 or challenge.lesson_id in revealed:
                status = "needs practice"
            elif current is not None and challenge.lesson_id == current.lesson_id:
                status = "seen"
            else:
                status = "not started"
            lesson_stages.append({"id": challenge.lesson_id, "status": status})

        quiz = self.get_level_quiz(level)
        quiz_questions = []
        quiz_correct = 0
        if quiz is not None:
            for question in quiz.questions:
                result = results.get(self._quiz_result_id(quiz, question), {})
                if result.get("score", 0) >= 1:
                    status = "correct answer"
                    quiz_correct += 1
                elif result.get("attempts", 0) > 0:
                    status = "needs practice"
                else:
                    status = "not started"
                quiz_questions.append({"id": question.question_id, "status": status})

        all_lessons_complete = len(completed) == len(path_challenges)
        if quiz is None:
            quiz_status = "not available"
        elif quiz_correct == len(quiz.questions):
            quiz_status = "completed"
        elif all_lessons_complete:
            quiz_status = "needs practice" if any(
                item["status"] == "needs practice" for item in quiz_questions
            ) else "not started"
        else:
            quiz_status = "locked"

        pre_assessment = self.assessment_summary("pre", data)
        post_assessment = self.assessment_summary("post", data)
        total_units = len(path_challenges) + len(quiz_questions) + 2
        completed_units = (
            len(completed)
            + quiz_correct
            + (1 if pre_assessment["completed"] else 0)
            + (1 if post_assessment["passed"] else 0)
        )
        percentage = round(100 * completed_units / total_units) if total_units else 0
        if not pre_assessment["completed"] and not completed and quiz_correct == 0:
            next_stage = "Pre-test assessment"
        elif current is not None:
            next_stage = f"Lesson: {current.lesson_id}"
        elif quiz is not None and quiz_status != "completed":
            next_question = next(
                (item["id"] for item in quiz_questions if item["status"] != "correct answer"),
                None,
            )
            next_stage = f"Quiz: {quiz.title} / {next_question}" if next_question else "Path complete"
        elif not pre_assessment["completed"]:
            next_stage = "Pre-test assessment"
        elif not post_assessment["passed"]:
            next_stage = "Post-test assessment"
        else:
            next_stage = "Path complete"
        return {
            "level": level,
            "completed": len(completed),
            "total": len(path_challenges),
            "quiz_correct": quiz_correct,
            "quiz_total": len(quiz_questions),
            "quiz_status": quiz_status,
            "percentage": percentage,
            "attempts": data.get("attempts", 0),
            "current_lesson": current.lesson_id if current else None,
            "next_stage": next_stage,
            "stages": lesson_stages,
            "quiz_questions": quiz_questions,
            "pre_assessment": pre_assessment,
            "post_assessment": post_assessment,
        }

    def reset_progress(self, confirmation):
        if confirmation != "RESET":
            return False
        self.store.save(default_progress())
        self.events.reset()
        self.events.append("progress_reset")
        return True

    def review_previous(self):
        data = self.store.load()
        for lesson_id in reversed(data.get("completed_lessons", [])):
            challenge = self.challenge_responder.loader.get_by_lesson(lesson_id)
            if challenge is not None:
                return challenge
        return None

    def _first_available_challenge(self, data):
        completed = set(data.get("completed_lessons", []))
        challenges = self._level_challenges(data.get("level"))
        allowed_lessons = {item.lesson_id for item in challenges}
        for challenge in challenges:
            if challenge.lesson_id in completed:
                continue
            if self._effective_prerequisites(challenge, allowed_lessons).issubset(completed):
                return challenge
        return None

    def _level_challenges(self, level):
        challenge_ids = self.level_loader.challenge_ids(level)
        if not challenge_ids:
            return self.challenge_responder.loader.all()
        start_id = self.level_loader.start_challenge_id(level)
        if start_id in challenge_ids:
            challenge_ids = [start_id, *(item for item in challenge_ids if item != start_id)]
        return [
            challenge
            for challenge_id in challenge_ids
            if (challenge := self.challenge_responder.loader.get(challenge_id)) is not None
        ]

    @staticmethod
    def _effective_prerequisites(challenge, allowed_lessons):
        return set(challenge.prerequisites).intersection(allowed_lessons)


def _show_intro(output, tr):
    output("========================================")
    output(f"  {tr.text('title', 'AI Platform Engineering Learning Tool')}")
    output("========================================")
    output(tr.text("tagline", "A practical path from DevOps/Platform/SRE into MLOps and LLMOps."))
    output(tr.text("phases", "Phases: P0 -> P1 -> P2 -> P3 -> P4 -> P5"))
    output(
        tr.text(
            "next_start",
            "Next action: choose option 1 to begin; progress is saved automatically.",
        )
    )


def _run_challenge_interaction(
    session,
    challenge,
    input_fn,
    output,
    *,
    supplied_answer=None,
    non_interactive=False,
    tr=None,
):
    tr = tr or Translator()
    output(
        tr.text(
            "next_answer",
            "Next action: enter your answer, or type 'show answer' to reveal the solution.",
        )
    )
    try:
        if challenge.challenge_id == DEFAULT_CHALLENGE_ID:
            answer = run_task(
                input_fn=input_fn,
                output=output,
                supplied_answer=supplied_answer,
                language=tr.language,
            )
        else:
            output(f"\n=== {challenge.lesson_id} ===\n")
            output(challenge.prompt)
            answer = capture_answer(
                input_fn=input_fn,
                output=output,
                supplied_answer=supplied_answer,
                language=tr.language,
            )
    except EOFError:
        structured_error(
            output,
            tr,
            tr.text("eof_what", "Input ended before the challenge was answered."),
            tr.text("eof_why", "The terminal provided no more readable input."),
            tr.text("eof_next", "Run `learn start` again to resume saved progress."),
        )
        return 130

    failed_attempts = 0
    remediation_shown = False
    while True:
        if str(answer).strip().casefold() == "show answer":
            solution, _ = session.reveal_solution(challenge.challenge_id)
            if solution is None:
                structured_error(
                    output,
                    tr,
                    "The worked solution is currently unavailable.",
                    "This lesson does not contain a revealable accepted answer.",
                    "Return to the menu and retry the lesson using its hint.",
                )
                return 2
            output(f"Worked solution: {solution}")
            output("This lesson is marked as revealed, not completed. Retry it later to complete it.")
            return 4

        # The answer returned by task_runner is scored in the production path.
        outcome, _ = session.evaluate_challenge(
            answer,
            challenge.challenge_id,
            feedback_stage=failed_attempts + 1,
        )
        if outcome.accepted:
            output(tr.text("correct", "Correct. Progress saved."))
            if outcome.feedback_correct:
                output(
                    tr.text(
                        "why_correct",
                        "Why it is correct: {reason}",
                        reason=outcome.feedback_correct,
                    )
                )
            return 0

        failed_attempts += 1
        if outcome.reason_code == "empty_answer":
            structured_error(
                output,
                tr,
                tr.text(
                    "empty_what",
                    "No answer provided. Progress was not completed.",
                ),
                tr.text(
                    "empty_why",
                    "An empty answer cannot demonstrate the requested command.",
                ),
                tr.text(
                    "empty_next",
                    "Enter a command from the lesson, then submit it again.",
                ),
            )
            if non_interactive:
                return 64
        else:
            structured_error(
                output,
                tr,
                tr.text(
                    "incorrect_what",
                    "Incorrect. {reason}",
                    reason=outcome.reason,
                ),
                tr.text(
                    "incorrect_why",
                    "It did not match the lesson's required command or concept.",
                ),
                tr.text(
                    "incorrect_next",
                    "Use the hint, revise the answer, and retry.",
                ),
            )
            if outcome.hint:
                output(f"Hint: {outcome.hint}")
            if non_interactive:
                return 2

        if failed_attempts >= 3 and not remediation_shown:
            if outcome.remediation:
                output(f"Explanation: {outcome.remediation}")
            if outcome.worked_example:
                output(f"Related example: {outcome.worked_example}")
            output("Retry now, or type 'show answer' to reveal this challenge's solution.")
            remediation_shown = True

        try:
            answer = capture_answer(input_fn=input_fn, output=output, language=tr.language)
        except EOFError:
            structured_error(
                output,
                tr,
                tr.text("eof_what", "Input ended before the challenge was answered."),
                tr.text("eof_why", "The terminal provided no more readable input."),
                tr.text("eof_next", "Run `learn start` again to resume saved progress."),
            )
            return 130


def _run_quiz_interaction(session, quiz, input_fn, output, tr=None):
    tr = tr or Translator()
    output(f"\n=== {quiz.title} ===")
    output("Answer every question correctly to complete this path.")
    output(tr.text("next_quiz", "Next action: answer each question; correct answers are saved."))
    for index, question in enumerate(quiz.questions, 1):
        if session.quiz_question_passed(quiz, question):
            output(f"Question {index}/{len(quiz.questions)} already completed.")
            continue
        while True:
            output(f"\nQuestion {index}/{len(quiz.questions)} [{question.question_type}]")
            output(question.prompt)
            for option in question.options:
                output(f"  {option}")
            try:
                answer = input_fn("Your answer: ")
            except EOFError:
                structured_error(
                    output,
                    tr,
                    tr.text(
                        "eof_what",
                        "Quiz paused. Saved answers will be resumed next time.",
                    ),
                    tr.text("eof_why", "The terminal provided no more readable input."),
                    tr.text("eof_next", "Run `learn start` again to resume saved answers."),
                )
                return 130
            outcome, _ = session.evaluate_quiz_answer(quiz, question, answer)
            if outcome.accepted:
                output("Correct. Answer saved.")
                break
            structured_error(
                output,
                tr,
                tr.text(
                    "incorrect_what",
                    "Incorrect. {reason}",
                    reason=outcome.reason,
                ),
                tr.text(
                    "incorrect_why",
                    "The answer did not satisfy this quiz question.",
                ),
                tr.text(
                    "incorrect_next",
                    "Use the hint, revise the answer, and retry.",
                ),
            )
            if outcome.hint:
                output(f"Hint: {outcome.hint}")
    output("Quiz complete. Results and completion time saved.")
    return 0


def _run_assessment_interaction(session, assessment, input_fn, output, tr=None):
    tr = tr or Translator()
    label = "Pre-test baseline" if assessment.kind == "pre" else "Post-test learning check"
    output(f"\n=== {label} ===")
    output(
        tr.text(
            "assessment_instruction",
            "Answer all 10 questions. Each topic appears exactly once.",
        )
    )
    output(tr.text("next_assessment", "Next action: choose only A or B for each question."))
    session.record_event("assessment_started", assessment=assessment.kind)
    started = monotonic()
    answers = {}
    for index, question in enumerate(assessment.questions, 1):
        while True:
            output(f"\nQuestion {index}/{len(assessment.questions)}")
            output(question.prompt)
            for option in question.options:
                output(f"  {option}")
            try:
                answer = input_fn(tr.text("assessment_choice", "Choose A or B: ")).strip()
            except EOFError:
                structured_error(
                    output,
                    tr,
                    tr.text("eof_what", "The assessment paused before completion."),
                    tr.text("eof_why", "No partial assessment score can be recorded."),
                    tr.text("eof_next", "Run `learn start` again and retake the assessment."),
                )
                return 130
            normalized = answer.split(".", 1)[0].strip().upper()
            if normalized in {"A", "B"}:
                answers[question.question_id] = normalized
                break
            structured_error(
                output,
                tr,
                tr.text("invalid_assessment_what", "The assessment answer is invalid."),
                tr.text("invalid_assessment_why", "This question accepts only A or B."),
                tr.text("invalid_assessment_next", "Enter A or B."),
            )
    result, _ = session.evaluate_assessment(
        assessment,
        answers,
        duration_seconds=round(monotonic() - started, 3),
    )
    output(f"{label} score: {result.correct}/{result.total} ({result.percentage}%).")
    if assessment.kind == "pre":
        output(tr.text("baseline_saved", "Baseline recorded. It does not block the learning path."))
        return 0
    if result.passed:
        output("Post-test passed. Learning evidence saved and the path is complete.")
        return 0
    output("Post-test needs another attempt: score at least 8/10 to complete the path.")
    return 2


def _select_level(session, level_choice, output, tr=None):
    tr = tr or Translator()
    try:
        level = session.select_level(level_choice)
    except ValueError:
        structured_error(
            output,
            tr,
            tr.text("level_what", "The learning level was not selected."),
            tr.text("level_why", "The input does not match an available level."),
            tr.text("level_next", "Enter 1, 2, 3, or an English level name."),
        )
        return None
    output(tr.text("selected_level", "Selected level: {level}", level=level))
    output(session.level_overview(level))
    return level


def _show_progress(session, output, tr=None):
    tr = tr or Translator()
    progress = session.progress_summary()
    output(tr.text("progress_heading", "Progress:"))
    output(f"  Level: {progress['level'] or 'not selected'}")
    output(f"  Path completion: {progress['percentage']}%")
    output(f"  Lessons completed: {progress['completed']}/{progress['total']}")
    output(
        f"  Quiz answers correct: {progress['quiz_correct']}/{progress['quiz_total']} "
        f"({progress['quiz_status']})"
    )
    pre = progress["pre_assessment"]
    post = progress["post_assessment"]
    output(
        f"  Pre-test: {pre['correct']}/{pre['total']} "
        f"({'completed' if pre['completed'] else 'not taken'})"
    )
    post_status = "passed" if post["passed"] else ("needs retry" if post["completed"] else "not taken")
    output(f"  Post-test: {post['correct']}/{post['total']} ({post_status})")
    output(f"  Attempts: {progress['attempts']}")
    output(f"  Current lesson: {progress['current_lesson'] or 'none'}")
    output(tr.text("next_stage", "  Next stage: {stage}", stage=progress["next_stage"]))
    if progress["stages"] or progress["quiz_questions"]:
        output("  Status legend: seen | needs practice | correct answer | completed")
    for stage in progress["stages"]:
        output(f"    Lesson [{stage['status']}]: {stage['id']}")
    for question in progress["quiz_questions"]:
        output(f"    Quiz [{question['status']}]: {question['id']}")


def _run_menu(session, input_fn, output, tr=None):
    tr = tr or Translator()
    while True:
        output("\n" + tr.text("menu", "Main menu:"))
        output(tr.text("menu_1", "  1. Continue"))
        output(tr.text("menu_2", "  2. Show progress"))
        output(tr.text("menu_3", "  3. Select path"))
        output(tr.text("menu_4", "  4. Review previous stage"))
        output(tr.text("menu_5", "  5. Exit"))
        output(tr.text("menu_6", "  6. Ask a roadmap question"))
        output(tr.text("menu_7", "  7. Reset all progress"))
        output(tr.text("menu_8", "  8. Take pre/post learning assessment"))
        output(tr.text("next_menu", "Next action: enter the number of your chosen option."))
        try:
            choice = input_fn(tr.text("menu_prompt", "Choose an option (1-8): ")).strip()
        except EOFError:
            structured_error(
                output,
                tr,
                tr.text("eof_what", "Input ended before a menu choice was entered."),
                tr.text("eof_why", "The terminal provided no more readable input."),
                tr.text("eof_next", "Run `learn start` again to resume saved progress."),
            )
            return 130

        if choice == "1":
            data = session.resume()
            selected_now = False
            if data.get("level") is None:
                try:
                    level_choice = input_fn(
                        tr.text(
                            "select_level_prompt",
                            "Select level (1 beginner, 2 intermediate, 3 experienced): ",
                        )
                    )
                except EOFError:
                    structured_error(
                        output,
                        tr,
                        tr.text("eof_what", "Input ended before a path was selected."),
                        tr.text("eof_why", "The terminal provided no more readable input."),
                        tr.text("eof_next", "Run `learn start` again and select a level."),
                    )
                    return 130
                if _select_level(session, level_choice, output, tr) is None:
                    continue
                selected_now = True
            if selected_now:
                code = _run_assessment_interaction(
                    session,
                    session.get_assessment("pre"),
                    input_fn,
                    output,
                    tr,
                )
                if code != 0:
                    return code
            challenge = session.get_continue_challenge()
            if challenge is None:
                quiz = session.get_pending_quiz()
                if quiz is not None:
                    output(f"Continuing with quiz: {quiz.title}")
                    return _run_quiz_interaction(session, quiz, input_fn, output, tr)
                pre = session.assessment_summary("pre")
                if not pre["completed"]:
                    return _run_assessment_interaction(
                        session, session.get_assessment("pre"), input_fn, output, tr
                    )
                post = session.assessment_summary("post")
                if not post["passed"]:
                    return _run_assessment_interaction(
                        session, session.get_assessment("post"), input_fn, output, tr
                    )
                output("Path complete: lessons, quiz, and post-test evidence are all complete.")
                continue
            output(f"Continuing from: {challenge.lesson_id}")
            return _run_challenge_interaction(session, challenge, input_fn, output, tr=tr)

        if choice == "2":
            _show_progress(session, output, tr)
            continue

        if choice == "3":
            try:
                level_choice = input_fn(
                    tr.text(
                        "select_level_prompt",
                        "Select level (1 beginner, 2 intermediate, 3 experienced): ",
                    )
                )
            except EOFError:
                structured_error(
                    output,
                    tr,
                    tr.text("eof_what", "Input ended before a path was selected."),
                    tr.text("eof_why", "The terminal provided no more readable input."),
                    tr.text("eof_next", "Run `learn start` again and select a level."),
                )
                return 130
            _select_level(session, level_choice, output, tr)
            continue

        if choice == "4":
            previous = session.review_previous()
            if previous is None:
                output("No completed stage is available to review yet.")
            else:
                output(f"Previous stage: {previous.lesson_id}")
                output(previous.prompt)
                output(f"Why it worked: {previous.feedback_correct}")
            continue

        if choice == "5":
            output(tr.text("goodbye", "Goodbye. Your progress is saved."))
            return 0

        if choice == "6":
            try:
                question = input_fn("What would you like to learn about? ")
            except EOFError:
                structured_error(
                    output,
                    tr,
                    tr.text("eof_what", "Input ended before a roadmap question was entered."),
                    tr.text("eof_why", "The terminal provided no more readable input."),
                    tr.text("eof_next", "Run `learn start` again and choose option 6."),
                )
                return 130
            try:
                answer = session.answer_roadmap_question(question)
            except RoadmapContentError as exc:
                structured_error(
                    output,
                    tr,
                    tr.text("content_what", "Roadmap content is unavailable."),
                    tr.text("content_why", "{reason}", reason=exc),
                    tr.text(
                        "content_next",
                        "Check the content files, then return to the main menu.",
                    ),
                )
                continue
            output(answer.render())
            continue

        if choice == "7":
            try:
                confirmation = input_fn(
                    "Type RESET to permanently clear all local progress, or press Enter to cancel: "
                ).strip()
            except EOFError:
                structured_error(
                    output,
                    tr,
                    "Reset canceled. Progress was not changed.",
                    "The exact RESET confirmation was not received before input ended.",
                    "Run `learn start` again; your existing progress is still available.",
                )
                return 130
            if session.reset_progress(confirmation):
                output("Progress reset confirmed. All local learning progress was cleared.")
            else:
                output("Reset canceled. Progress was not changed.")
            continue

        if choice == "8":
            data = session.resume()
            if data.get("level") is None:
                structured_error(
                    output,
                    tr,
                    tr.text("no_path_what", "No learning path is selected."),
                    tr.text("no_path_why", "The assessment depends on a selected level."),
                    tr.text("no_path_next", "Choose option 3 first."),
                )
                continue
            pre = session.assessment_summary("pre", data)
            if not pre["completed"]:
                return _run_assessment_interaction(
                    session, session.get_assessment("pre"), input_fn, output, tr
                )
            if not session.learning_content_complete(data):
                structured_error(
                    output,
                    tr,
                    tr.text("locked_what", "The post-test is still locked."),
                    tr.text(
                        "locked_why",
                        "Not all lessons and quiz questions are complete.",
                    ),
                    tr.text(
                        "locked_next",
                        "Choose option 1 and complete the next path stage.",
                    ),
                )
                continue
            return _run_assessment_interaction(
                session, session.get_assessment("post"), input_fn, output, tr
            )

        structured_error(
            output,
            tr,
            tr.text("invalid_menu_what", "The menu choice is invalid."),
            tr.text("invalid_menu_why", "The menu accepts only options 1 through 8."),
            tr.text("invalid_menu_next", "Enter a number from 1 to 8."),
        )


def run_cli(args, input_fn=input, output=print):
    tr = Translator(getattr(args, "lang", "en") or "en")
    session = Session(state_path=args.state_path)
    before = session.init()
    session.record_event("session_started", interactive=not args.non_interactive)
    if not before.get("level") and not before.get("completed_lessons"):
        session.record_event("onboarding_started")

    _show_intro(output, tr)
    if before.get("level") or before.get("completed_lessons"):
        output(
            f"Resuming previous session: {len(before.get('completed_lessons', []))} lesson(s) completed."
        )

    backend, model = session.select_model()
    output(tr.text("active_model", "Active local model: {backend}/{model}", backend=backend, model=model))
    if backend == "ollama":
        output(
            tr.text(
                "inference_ollama",
                "Inference scope: loopback Ollama with local Knowledge Base grounding.",
            )
        )
    elif backend == "vllm":
        output(
            tr.text(
                "inference_vllm",
                "Inference scope: loopback vLLM with local Knowledge Base grounding.",
            )
        )
    else:
        output(
            tr.text(
                "inference_fallback",
                "Inference scope: deterministic local Knowledge Base fallback; no network used.",
            )
        )

    if not args.non_interactive and args.level is None:
        return _run_menu(session, input_fn, output, tr)

    if args.level is None:
        structured_error(
            output,
            tr,
            tr.text("missing_level_what", "Non-interactive mode has no level."),
            tr.text("missing_level_why", "The --level option is required."),
            tr.text("missing_level_next", "Run again with --level 1."),
        )
        return 64
    if _select_level(session, args.level, output, tr) is None:
        return 64
    if args.non_interactive and args.answer is None:
        structured_error(
            output,
            tr,
            tr.text("missing_answer_what", "Non-interactive mode has no answer."),
            tr.text("missing_answer_why", "The --answer option is required."),
            tr.text("missing_answer_next", "Run again with --answer and the exercise answer."),
        )
        return 64

    challenge = session.get_continue_challenge()
    if challenge is None:
        quiz = session.get_pending_quiz()
        if quiz is not None:
            output("The path quiz is pending. Run `learn start` interactively to complete it.")
            return 4
        output("All currently available lessons for this path are complete.")
        return 0
    return _run_challenge_interaction(
        session,
        challenge,
        input_fn,
        output,
        supplied_answer=args.answer,
        non_interactive=args.non_interactive,
        tr=tr,
    )


def build_parser():
    parser = argparse.ArgumentParser(prog="learn")
    parser.add_argument("command", nargs="?", default="start", choices=("start",))
    parser.add_argument("--level")
    # PowerShell can omit an explicitly empty string when forwarding arguments.
    # Treat a present --answer with no value as the intended empty answer.
    parser.add_argument("--answer", nargs="?", const="")
    parser.add_argument("--state-path")
    parser.add_argument("--lang", choices=SUPPORTED_LANGUAGES, default="en")
    parser.add_argument("--non-interactive", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run_cli(args)
    except (
        AssessmentContentError,
        ContentValidationError,
        ProgressLoadError,
        ProgressSaveError,
        RoadmapContentError,
    ) as exc:
        tr = Translator(getattr(args, "lang", "en") or "en")
        structured_error(
            lambda message: print(message, file=sys.stderr),
            tr,
            tr.text("fatal_what", "Progress could not be loaded or saved."),
            tr.text("fatal_why", "{reason}", reason=exc),
            tr.text(
                "fatal_next",
                "Check file permissions and content files, then run the command again.",
            ),
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validated local lesson and quiz loading plus deterministic quiz scoring."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from scoring.challenge_scorer import ChallengeScorer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEVELS_PATH = PROJECT_ROOT / "content" / "levels.json"
DEFAULT_TASKS_DIR = PROJECT_ROOT / "content" / "tasks"
QUESTION_TYPES = ("command", "multiple_choice", "free_response")


class ContentValidationError(ValueError):
    """Raised when bundled learning content does not match its schema."""


@dataclass(frozen=True)
class QuizQuestion:
    question_id: str
    question_type: str
    prompt: str
    accepted_answers: tuple[str, ...]
    options: tuple[str, ...] = ()
    accepted_keywords: tuple[str, ...] = ()
    min_keywords: int = 1
    hint: str = "Review the lesson and try again."


@dataclass(frozen=True)
class QuizDefinition:
    quiz_id: str
    title: str
    questions: tuple[QuizQuestion, ...]


@dataclass(frozen=True)
class QuizOutcome:
    accepted: bool
    reason: str
    hint: str | None


class LessonLoader:
    def __init__(self, levels_path=None, tasks_dir=None):
        self.levels_path = Path(levels_path).resolve() if levels_path else DEFAULT_LEVELS_PATH
        self.tasks_dir = Path(tasks_dir).resolve() if tasks_dir else DEFAULT_TASKS_DIR

    def load(self, path=None):
        source = Path(path).resolve() if path else self.levels_path
        data = self._read_json(source)
        if data.get("schema_version") != "1.0.0":
            raise ContentValidationError("Invalid level schema: schema_version must be 1.0.0.")
        levels = data.get("levels")
        if not isinstance(levels, dict) or not levels:
            raise ContentValidationError("Invalid level schema: 'levels' must be a non-empty object.")
        for level, definition in levels.items():
            if not isinstance(definition, dict):
                raise ContentValidationError(f"Invalid level schema: '{level}' must be an object.")
            for field in ("lesson", "exercise", "quiz"):
                if not isinstance(definition.get(field), str) or not definition[field].strip():
                    raise ContentValidationError(
                        f"Invalid level schema: '{level}.{field}' must be a filename."
                    )
        return data

    def load_lesson(self, lesson_file):
        path = self._safe_content_path(lesson_file)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise ContentValidationError(f"Learning content is empty: {lesson_file}")
        return {"file": lesson_file, "text": text}

    def load_quiz(self, quiz_file):
        raw = self._read_json(self._safe_content_path(quiz_file))
        if raw.get("schema_version") != "1.0.0":
            raise ContentValidationError(
                f"Invalid quiz schema in {quiz_file}: schema_version must be 1.0.0."
            )
        quiz_id = self._required_text(raw, "quiz_id", quiz_file)
        title = self._required_text(raw, "title", quiz_file)
        raw_questions = raw.get("questions")
        if not isinstance(raw_questions, list) or not raw_questions:
            raise ContentValidationError(f"Invalid quiz schema in {quiz_file}: questions are required.")

        questions = tuple(self._build_question(item, quiz_file) for item in raw_questions)
        ids = [question.question_id for question in questions]
        if len(ids) != len(set(ids)):
            raise ContentValidationError(f"Invalid quiz schema in {quiz_file}: duplicate question id.")
        return QuizDefinition(quiz_id=quiz_id, title=title, questions=questions)

    def _build_question(self, raw, source):
        if not isinstance(raw, dict):
            raise ContentValidationError(f"Invalid quiz schema in {source}: question must be an object.")
        question_id = self._required_text(raw, "id", source)
        question_type = self._required_text(raw, "type", source)
        prompt = self._required_text(raw, "prompt", source)
        if question_type not in QUESTION_TYPES:
            raise ContentValidationError(
                f"Invalid quiz schema in {source}: unsupported type '{question_type}'."
            )

        accepted_answers = self._text_tuple(raw.get("accepted_answers"))
        options = self._text_tuple(raw.get("options"))
        keywords = self._text_tuple(raw.get("accepted_keywords"))
        min_keywords = raw.get("min_keywords", 1)
        if question_type in ("command", "multiple_choice") and not accepted_answers:
            raise ContentValidationError(
                f"Invalid quiz schema in {source}: {question_id} needs accepted_answers."
            )
        if question_type == "multiple_choice" and len(options) < 2:
            raise ContentValidationError(
                f"Invalid quiz schema in {source}: {question_id} needs at least two options."
            )
        if question_type == "free_response" and not keywords:
            raise ContentValidationError(
                f"Invalid quiz schema in {source}: {question_id} needs accepted_keywords."
            )
        if not isinstance(min_keywords, int) or not 1 <= min_keywords <= max(len(keywords), 1):
            raise ContentValidationError(
                f"Invalid quiz schema in {source}: {question_id} has invalid min_keywords."
            )
        return QuizQuestion(
            question_id=question_id,
            question_type=question_type,
            prompt=prompt,
            accepted_answers=accepted_answers,
            options=options,
            accepted_keywords=keywords,
            min_keywords=min_keywords,
            hint=str(raw.get("hint") or "Review the lesson and try again."),
        )

    def _safe_content_path(self, filename):
        if not isinstance(filename, str) or not filename.strip():
            raise ContentValidationError("Content filename must be a non-empty string.")
        path = (self.tasks_dir / filename).resolve()
        if path != self.tasks_dir and self.tasks_dir not in path.parents:
            raise ContentValidationError("Content path must stay inside the tasks directory.")
        return path

    @staticmethod
    def _read_json(path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ContentValidationError(f"Content file not found: {path.name}") from exc
        except json.JSONDecodeError as exc:
            raise ContentValidationError(f"Content JSON is invalid: {path.name}") from exc
        if not isinstance(data, dict):
            raise ContentValidationError(f"Content JSON must be an object: {path.name}")
        return data

    @staticmethod
    def _required_text(raw, field, source):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ContentValidationError(f"Invalid schema in {source}: '{field}' is required.")
        return value.strip()

    @staticmethod
    def _text_tuple(value):
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


class QuizEngine:
    TYPES = QUESTION_TYPES

    def __init__(self, quiz, scorer=None):
        self.quiz = quiz
        self.scorer = scorer or ChallengeScorer()

    def all_answered(self, answers):
        if not isinstance(answers, dict):
            return False
        return all(
            isinstance(answers.get(question.question_id), str)
            and bool(answers[question.question_id].strip())
            for question in self.quiz.questions
        )

    def evaluate(self, question, answer):
        normalized = str(answer or "").strip()
        if not normalized:
            return QuizOutcome(False, "No answer was provided.", question.hint)
        if question.question_type == "command":
            accepted = self.scorer.score(normalized, question.accepted_answers)
        elif question.question_type == "multiple_choice":
            accepted = normalized.casefold() in {
                candidate.casefold() for candidate in question.accepted_answers
            }
        else:
            words = normalized.casefold()
            matches = sum(
                1 for keyword in question.accepted_keywords if keyword.casefold() in words
            )
            accepted = matches >= question.min_keywords
        if accepted:
            return QuizOutcome(True, "Correct.", None)
        return QuizOutcome(False, "That answer is not correct yet.", question.hint)

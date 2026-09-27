#!/usr/bin/env python3
"""Load the local, level-specific learning path content."""
from __future__ import annotations

import json
from pathlib import Path

from content.lesson_loader import LessonLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEVELS_PATH = PROJECT_ROOT / "content" / "levels.json"
DEFAULT_TASKS_DIR = PROJECT_ROOT / "content" / "tasks"


class LevelLoader:
    def __init__(self, path=None, tasks_dir=None):
        self.path = Path(path).resolve() if path else DEFAULT_LEVELS_PATH
        self.tasks_dir = Path(tasks_dir).resolve() if tasks_dir else DEFAULT_TASKS_DIR
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.glossary = self.data.get("glossary", {})
        self.content_loader = LessonLoader(self.path, self.tasks_dir)

    def levels(self):
        return tuple(self.data.get("levels", {}))

    def definition(self, level):
        return self.data.get("levels", {}).get(level)

    def prerequisites(self, level):
        definition = self.definition(level) or {}
        return list(definition.get("prerequisites", []))

    def challenge_ids(self, level):
        definition = self.definition(level) or {}
        return list(definition.get("challenge_ids", []))

    def start_challenge_id(self, level):
        definition = self.definition(level) or {}
        return definition.get("start_challenge_id")

    def explain_glossary(self, term):
        return self.glossary.get(term, f"No definition for {term}.")

    def roadmap_if_missing(self, level):
        definition = self.definition(level)
        if definition is None:
            return self._roadmap(level, "the level definition is unavailable")

        missing = [
            kind
            for kind in ("lesson", "exercise", "quiz")
            if not self._content_path(definition.get(kind)).is_file()
        ]
        if missing:
            return self._roadmap(level, f"missing {', '.join(missing)} content")
        return None

    def render_level(self, level):
        definition = self.definition(level)
        if definition is None:
            return self._roadmap(level, "the level definition is unavailable")

        fallback = self.roadmap_if_missing(level)
        if fallback:
            return fallback

        lines = ["Key terms (read these before the learning material):"]
        for term, explanation in self.glossary.items():
            lines.append(f"- {term}: {explanation}")
        prerequisites = self.prerequisites(level)
        lines.extend(
            [
                "",
                f"Path: {level}",
                "Prerequisites: " + (", ".join(prerequisites) if prerequisites else "None"),
            ]
        )
        for kind in ("lesson", "exercise", "quiz"):
            if kind == "quiz":
                quiz = self.content_loader.load_quiz(definition[kind])
                quiz_lines = [f"# {quiz.title}"]
                for index, question in enumerate(quiz.questions, 1):
                    quiz_lines.append(f"{index}. {question.prompt}")
                    quiz_lines.extend(f"   {option}" for option in question.options)
                content = "\n".join(quiz_lines)
            else:
                content = self._content_path(definition[kind]).read_text(encoding="utf-8").strip()
            lines.extend(["", f"--- {kind.title()} ---", content])
        return "\n".join(lines)

    def _content_path(self, filename):
        return self.tasks_dir / filename if filename else self.tasks_dir / "__missing__"

    @staticmethod
    def _roadmap(level, reason):
        return (
            f"Roadmap overview for {level}: detailed content is not available ({reason}).\n"
            "Continue without getting stuck: P0 platform bridge -> P1 ML literacy -> "
            "P2 MLOps -> P3 orchestration -> P4 LLMOps/inference and GPU scheduling.\n"
            "Next action: return to Select path and choose another available level."
        )

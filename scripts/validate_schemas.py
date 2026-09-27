#!/usr/bin/env python3
"""Validate repository JSON plus cross-file learning-content relationships."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from content.assessment import AssessmentLoader
from content.lesson_loader import LessonLoader
from content.roadmap_explorer import KnowledgeBaseLoader
from persist.progress_store import default_progress
from scoring.challenge_loader import ChallengeLoader


class SchemaValidationError(ValueError):
    pass


def _read_object(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(f"Invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise SchemaValidationError(f"JSON root must be an object: {path.relative_to(ROOT)}")
    return data


def validate_repository():
    json_paths = sorted((ROOT / "content").rglob("*.json")) + sorted(
        (ROOT / "contracts").glob("*.json")
    )
    if not json_paths:
        raise SchemaValidationError("No content or contract JSON files were found.")
    parsed = {path: _read_object(path) for path in json_paths}

    lesson_loader = LessonLoader()
    levels = lesson_loader.load()
    for level, definition in levels["levels"].items():
        for field in ("lesson", "exercise"):
            if lesson_loader.load_lesson(definition[field]) is None:
                raise SchemaValidationError(f"Missing {field} content for level: {level}")
        lesson_loader.load_quiz(definition["quiz"])

    challenges = ChallengeLoader().all()
    challenge_ids = [item.challenge_id for item in challenges]
    lesson_ids = {item.lesson_id for item in challenges}
    if not challenges or len(challenge_ids) != len(set(challenge_ids)):
        raise SchemaValidationError("Challenge ids must be present and unique.")
    for challenge in challenges:
        if not challenge.accepted_answers:
            raise SchemaValidationError(f"Challenge has no accepted answer: {challenge.challenge_id}")
        missing = set(challenge.prerequisites) - lesson_ids
        if missing:
            raise SchemaValidationError(
                f"Unknown prerequisites for {challenge.challenge_id}: {sorted(missing)}"
            )
    known_challenges = set(challenge_ids)
    for level, definition in levels["levels"].items():
        configured = definition.get("challenge_ids", [])
        if definition.get("start_challenge_id") not in configured:
            raise SchemaValidationError(f"Start challenge is not in {level}.challenge_ids")
        missing = set(configured) - known_challenges
        if missing:
            raise SchemaValidationError(f"Unknown challenge ids for {level}: {sorted(missing)}")

    knowledge = KnowledgeBaseLoader().load()
    topic_ids = [item["topic_id"] for item in knowledge["topics"]]
    if len(topic_ids) != len(set(topic_ids)):
        raise SchemaValidationError("Knowledge Base topic ids must be unique.")
    known_topics = set(topic_ids)
    for item in knowledge["topics"]:
        missing = set(item["related_topics"]) - known_topics
        if missing:
            raise SchemaValidationError(
                f"Unknown related topics for {item['topic_id']}: {sorted(missing)}"
            )

    assessment = AssessmentLoader().load("pre")
    AssessmentLoader().load("post")
    missing_assessment_topics = {item.topic_id for item in assessment.questions} - known_topics
    if missing_assessment_topics:
        raise SchemaValidationError(
            f"Unknown assessment topics: {sorted(missing_assessment_topics)}"
        )

    progress_contract = parsed[ROOT / "contracts" / "progress-record.json"]
    if set(progress_contract.get("fields", {})) != set(default_progress()):
        raise SchemaValidationError("Progress contract fields do not match runtime state.")
    command_contract = parsed[ROOT / "contracts" / "command-schema.json"]
    command_names = {item.get("name") for item in command_contract.get("commands", [])}
    if "learn start" not in command_names:
        raise SchemaValidationError("Command contract must define learn start.")

    return len(json_paths)


def main():
    try:
        count = validate_repository()
    except (SchemaValidationError, ValueError, KeyError, TypeError) as exc:
        print(f"Schema validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Schema validation passed: {count} JSON files and cross-file references checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

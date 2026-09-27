#!/usr/bin/env python3
"""Versioned, atomic persistence for learner progress."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.0.0"
SCHEMA_VERSION_PARTS = (1, 0, 0)


class ProgressSaveError(RuntimeError):
    """Raised when progress cannot be persisted without risking existing state."""


class ProgressLoadError(RuntimeError):
    """Raised when a state file cannot be safely interpreted or migrated."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def default_progress(timestamp=None):
    now = timestamp or utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "level": None,
        "completed_lessons": [],
        "quiz_results": [],
        "attempts": 0,
        "current_lesson": None,
        "path_switches": [],
        "revealed_lessons": [],
        "timestamps": {
            "created_at": now,
            "updated_at": now,
            "last_session_at": None,
        },
    }


class ProgressStore:
    def __init__(self, path=".local/state/progress.json"):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return default_progress()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            return self._recover_corrupt_file()

        if not isinstance(raw, dict):
            return self._recover_corrupt_file()

        version = self._parse_version(raw.get("schema_version"))
        if version is not None and version > SCHEMA_VERSION_PARTS:
            raise ProgressLoadError(
                f"Progress schema {raw['schema_version']} is newer than supported {SCHEMA_VERSION}. "
                "Upgrade the learning tool before continuing."
            )

        migrated = self._canonicalize(raw)
        if migrated != raw:
            try:
                self.save(migrated, touch_updated_at=False)
            except ProgressSaveError:
                # Read-only storage must not turn valid legacy data into corruption.
                pass
        return migrated

    def save(self, data, *, touch_updated_at=True):
        canonical = self._canonicalize(data)
        if touch_updated_at:
            canonical["timestamps"]["updated_at"] = utc_now()

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(canonical, indent=2), encoding="utf-8")
            os.replace(str(tmp), str(self.path))
        except (OSError, TypeError, ValueError) as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ProgressSaveError(f"Could not save progress to {self.path}") from exc
        return canonical

    @staticmethod
    def _parse_version(value):
        if value is None:
            return None
        try:
            parts = tuple(int(part) for part in str(value).split("."))
        except ValueError as exc:
            raise ProgressLoadError(f"Invalid progress schema version: {value}") from exc
        if len(parts) != 3 or any(part < 0 for part in parts):
            raise ProgressLoadError(f"Invalid progress schema version: {value}")
        return parts

    def _canonicalize(self, raw):
        now = utc_now()
        record = default_progress(now)

        level = raw.get("level")
        record["level"] = level if level in (None, "beginner", "intermediate", "experienced") else None
        record["completed_lessons"] = self._unique_strings(
            raw.get("completed_lessons", raw.get("completed", []))
        )
        record["revealed_lessons"] = self._unique_strings(
            raw.get("revealed_lessons", raw.get("revealed", []))
        )
        record["quiz_results"] = self._unique_quiz_results(raw.get("quiz_results", []))

        attempts = raw.get("attempts", 0)
        record["attempts"] = attempts if isinstance(attempts, int) and attempts >= 0 else 0
        current_lesson = raw.get("current_lesson")
        record["current_lesson"] = current_lesson if isinstance(current_lesson, str) else None
        record["path_switches"] = self._unique_path_switches(raw.get("path_switches", []))

        timestamps = raw.get("timestamps") if isinstance(raw.get("timestamps"), dict) else {}
        legacy_last_session = raw.get("last_session")
        record["timestamps"] = {
            "created_at": timestamps.get("created_at") or legacy_last_session or now,
            "updated_at": timestamps.get("updated_at") or legacy_last_session or now,
            "last_session_at": timestamps.get("last_session_at") or legacy_last_session,
        }
        return record

    def _recover_corrupt_file(self):
        backup = self.path.with_suffix(self.path.suffix + ".bad")
        try:
            os.replace(str(self.path), str(backup))
        except OSError:
            pass
        return default_progress()

    @staticmethod
    def _unique_strings(values):
        if not isinstance(values, list):
            return []
        return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))

    @staticmethod
    def _unique_quiz_results(values):
        if not isinstance(values, list):
            return []
        by_question = {}
        for value in values:
            if not isinstance(value, dict) or not isinstance(value.get("question_id"), str):
                continue
            item = deepcopy(value)
            score = item.get("score", 0)
            item["score"] = score if isinstance(score, (int, float)) and 0 <= score <= 1 else 0
            attempts = item.get("attempts", 0)
            item["attempts"] = attempts if isinstance(attempts, int) and attempts >= 0 else 0
            question_id = item["question_id"]
            previous = by_question.get(question_id)
            if previous is None:
                by_question[question_id] = item
                continue
            previous["score"] = max(previous["score"], item["score"])
            previous["attempts"] += item["attempts"]
            if item.get("timestamp"):
                previous["timestamp"] = item["timestamp"]
        return list(by_question.values())

    @staticmethod
    def _unique_path_switches(values):
        if not isinstance(values, list):
            return []
        unique = []
        seen = set()
        for value in values:
            if not isinstance(value, dict):
                continue
            key = (value.get("from_level"), value.get("to_level"), value.get("timestamp"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(deepcopy(value))
        return unique

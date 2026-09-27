#!/usr/bin/env python3
"""Append-only local JSONL events used for duration measurement."""
from __future__ import annotations

import json
from pathlib import Path

from persist.progress_store import utc_now


class EventStore:
    def __init__(self, path):
        self.path = Path(path)

    def append(self, event_type, **details):
        event = {"event_type": event_type, "timestamp": utc_now(), **details}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            return False
        return True

    def read(self):
        if not self.path.exists():
            return []
        events = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and isinstance(event.get("event_type"), str):
                events.append(event)
        return events

    def has_event(self, event_type):
        return any(event.get("event_type") == event_type for event in self.read())

    def reset(self):
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            return False
        return True

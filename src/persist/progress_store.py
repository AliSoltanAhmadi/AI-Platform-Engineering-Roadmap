#!/usr/bin/env python3
"""Persist progress record per FR-006 / data-model.md."""
import json
from pathlib import Path

class ProgressStore:
    def __init__(self, path=".local/state/progress.json"):
        self.path = Path(path)

    def load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"schema_version":"1.0.0","level":None,"completed":[],"last_session":None}

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))

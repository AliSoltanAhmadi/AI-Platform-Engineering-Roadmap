#!/usr/bin/env python3
"""Persist progress record per FR-006 / data-model.md."""
import json
import os
from pathlib import Path

class ProgressSaveError(RuntimeError):
    """Raised when progress cannot be persisted without risking existing state."""

class ProgressStore:
    def __init__(self, path=".local/state/progress.json"):
        self.path = Path(path)

    def load(self):
        default = {"schema_version":"1.0.0","level":None,"completed":[],"last_session":None}
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                # Graceful: backup corrupt file, return default
                bad = self.path.with_suffix(self.path.suffix + ".bad")
                try:
                    self.path.rename(bad)
                except Exception:
                    pass
                return default
        return default

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(str(tmp), str(self.path))
        except (OSError, TypeError, ValueError) as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ProgressSaveError(f"Could not save progress to {self.path}") from exc

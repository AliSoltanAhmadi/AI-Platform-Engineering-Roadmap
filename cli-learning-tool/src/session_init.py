#!/usr/bin/env python3
"""T013: Session initialization - creates .local/state/progress.json on first launch."""
import json
import os
from pathlib import Path

PROGRESS_PATH = Path(".local/state/progress.json")

DEFAULT = {
    "schema_version": "1.0.0",
    "level": None,
    "completed": [],
    "last_session": None
}

def init():
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, "w") as f:
            json.dump(DEFAULT, f, indent=2)
        print("[session_init] Created new progress file.")
    else:
        print("[session_init] Progress file exists.")

if __name__ == "__main__":
    init()

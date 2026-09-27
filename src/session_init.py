#!/usr/bin/env python3
"""T013: Session initialization - creates .local/state/progress.json on first launch."""
from pathlib import Path

from persist.progress_store import ProgressStore

PROGRESS_PATH = Path(".local/state/progress.json")

def init():
    store = ProgressStore(PROGRESS_PATH)
    if not store.path.exists():
        store.save(store.load())
        print("[session_init] Created new progress file.")
    else:
        store.load()
        print("[session_init] Progress file exists.")

if __name__ == "__main__":
    init()

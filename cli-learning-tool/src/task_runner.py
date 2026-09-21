#!/usr/bin/env python3
"""T015: Interactive task runner - displays markdown content and captures user free-response answers."""
import sys
from pathlib import Path

def run_task(task_path: str = None):
    if task_path is None:
        base = Path(__file__).resolve().parent.parent
        task_path = base / "content" / "tasks" / "beginner_first_task.md"
    p = Path(task_path)
    if not p.exists():
        print(f"[task_runner] Task file not found: {p}")
        sys.exit(1)
    content = p.read_text(encoding="utf-8")
    print("\n=== BEGINNER FIRST TASK ===\n")
    print(content)
    print("\n--- Your answer (free response) ---")
    try:
        answer = input("> ")
    except EOFError:
        answer = ""
    print(f"[task_runner] Captured answer: {answer}")
    return answer

if __name__ == "__main__":
    ans = run_task()
    # Exit 0 for success; validation uses stdout
    print(f"\n[task_runner] Done. Answer length: {len(ans)} chars.")

#!/usr/bin/env python3
"""Display a task and return the learner's free-response answer."""
from pathlib import Path


DEFAULT_TASK_PATH = (
    Path(__file__).resolve().parent.parent
    / "content"
    / "tasks"
    / "beginner_first_task.md"
)
DEFAULT_FA_TASK_PATH = DEFAULT_TASK_PATH.with_name("beginner_first_task.fa.md")


def show_task(task_path=None, output=print, language="en"):
    """Render task content through the caller-provided output function."""
    path = Path(task_path) if task_path else (
        DEFAULT_FA_TASK_PATH if language == "fa" else DEFAULT_TASK_PATH
    )
    if path.exists():
        content = path.read_text(encoding="utf-8")
    else:
        content = "First challenge: pull the nginx container image."
    heading = "اولین تمرین مبتدی" if language == "fa" else "BEGINNER FIRST TASK"
    output(f"\n=== {heading} ===\n")
    output(content)


def capture_answer(input_fn=input, output=print, supplied_answer=None, language="en"):
    """Capture or forward one answer without scoring it."""
    if language == "fa":
        output("\n--- پاسخ شما (متن آزاد) ---")
        output("یک فرمان وارد کنید؛ برای دیدن راه‌حل بدون تکمیل درس بنویسید: show answer")
    else:
        output("\n--- Your answer (free response) ---")
        output("Enter a command, or type 'show answer' to reveal the solution without completing the lesson.")
    answer = input_fn("> ") if supplied_answer is None else supplied_answer
    return answer


def run_task(task_path=None, input_fn=input, output=print, supplied_answer=None, language="en"):
    """Run the task interaction and return its answer to the orchestrator."""
    show_task(task_path=task_path, output=output, language=language)
    return capture_answer(
        input_fn=input_fn,
        output=output,
        supplied_answer=supplied_answer,
        language=language,
    )


if __name__ == "__main__":
    answer = run_task()
    print(f"\n[task_runner] Done. Answer length: {len(answer)} chars.")

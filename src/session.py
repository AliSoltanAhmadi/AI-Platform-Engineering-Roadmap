#!/usr/bin/env python3
"""Interactive session orchestration used by both production and E2E tests."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from llm.model_selector import ModelSelector
from persist.progress_store import ProgressSaveError, ProgressStore
from scoring.challenge_scorer import ChallengeScorer
from task_runner import capture_answer, run_task

DEFAULT_ACCEPTED = ("docker pull nginx", "podman pull nginx")
LESSON_ID = "beginner-first-task"


class Session:
    def __init__(self, state_path=None):
        self.path = Path(state_path) if state_path else Path(".local/state/progress.json")
        self.store = ProgressStore(path=str(self.path))
        self.scorer = ChallengeScorer()
        self.model_selector = ModelSelector()

    def init(self):
        if not self.path.exists():
            self.store.save(
                {
                    "schema_version": "1.0.0",
                    "level": None,
                    "completed": [],
                    "last_session": None,
                    "attempts": 0,
                }
            )
        return self.store.load()

    def select_level(self, choice="1"):
        mapping = {"1": "beginner", "2": "intermediate", "3": "experienced"}
        normalized = str(choice).strip().lower()
        reverse = {value: value for value in mapping.values()}
        level = mapping.get(normalized, reverse.get(normalized))
        if level is None:
            raise ValueError("Level must be 1, 2, 3, beginner, intermediate, or experienced")
        data = self.store.load()
        data["level"] = level
        self.store.save(data)
        return level

    def select_model(self):
        return self.model_selector.select()

    def run_challenge(self, answer, accepted=None):
        accepted_answers = accepted or DEFAULT_ACCEPTED
        correct = self.scorer.score(answer, accepted_answers)
        data = self.store.load()
        data["attempts"] = data.get("attempts", 0) + 1
        if correct:
            completed = data.setdefault("completed", [])
            if LESSON_ID not in completed:
                completed.append(LESSON_ID)
            data["last_session"] = datetime.now(timezone.utc).isoformat()
        self.store.save(data)
        return correct, data

    def resume(self):
        return self.store.load()


def _show_intro(output):
    output("========================================")
    output("  AI Platform Engineering Learning Tool")
    output("========================================")
    output("A practical path from DevOps/Platform/SRE into MLOps and LLMOps.")
    output("Phases: P0 -> P1 -> P2 -> P3 -> P4 -> P5")


def run_cli(args, input_fn=input, output=print):
    session = Session(state_path=args.state_path)
    before = session.init()

    _show_intro(output)
    if before.get("level") or before.get("completed"):
        output(
            f"Resuming previous session: {len(before.get('completed', []))} lesson(s) completed."
        )

    backend, model = session.select_model()
    output(f"Active local model: {backend}/{model}")

    if args.level is not None:
        level_choice = args.level
    elif args.non_interactive:
        output("Missing --level in non-interactive mode.")
        return 64
    else:
        level_choice = input_fn("Select level (1 beginner, 2 intermediate, 3 experienced): ")

    try:
        level = session.select_level(level_choice)
    except ValueError as exc:
        output(str(exc))
        return 64

    output(f"Selected level: {level}")
    if args.non_interactive and args.answer is None:
        output("Missing --answer in non-interactive mode.")
        return 64

    try:
        answer = run_task(
            input_fn=input_fn,
            output=output,
            supplied_answer=args.answer,
        )
    except EOFError:
        output("Input ended before the challenge was answered.")
        return 130

    while True:
        # The answer returned by task_runner is scored in the production path.
        correct, _ = session.run_challenge(answer)
        if correct:
            output("Correct. Progress saved.")
            return 0

        if not str(answer).strip():
            output("No answer provided. Progress was not completed.")
            if args.non_interactive:
                return 64
        else:
            output("Incorrect. Hint: use the container runtime, then the pull command, then nginx.")
            if args.non_interactive:
                return 2

        try:
            answer = capture_answer(input_fn=input_fn, output=output)
        except EOFError:
            output("Input ended before the challenge was answered.")
            return 130


def build_parser():
    parser = argparse.ArgumentParser(prog="learn")
    parser.add_argument("command", nargs="?", default="start", choices=("start",))
    parser.add_argument("--level")
    # PowerShell can omit an explicitly empty string when forwarding arguments.
    # Treat a present --answer with no value as the intended empty answer.
    parser.add_argument("--answer", nargs="?", const="")
    parser.add_argument("--state-path")
    parser.add_argument("--non-interactive", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run_cli(args)
    except ProgressSaveError as exc:
        print(f"Progress could not be saved: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

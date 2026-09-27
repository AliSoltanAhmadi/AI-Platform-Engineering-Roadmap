#!/usr/bin/env python3
"""Interactive session orchestration used by both production and E2E tests."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from llm.model_selector import ModelSelector
from persist.progress_store import ProgressLoadError, ProgressSaveError, ProgressStore, utc_now
from scoring.challenge_loader import ChallengeLoader, ChallengeResponder
from task_runner import capture_answer, run_task

DEFAULT_CHALLENGE_ID = "challenge-pull-image"


class Session:
    def __init__(self, state_path=None, challenge_path=None):
        self.path = Path(state_path) if state_path else Path(".local/state/progress.json")
        self.store = ProgressStore(path=str(self.path))
        self.challenge_responder = ChallengeResponder(ChallengeLoader(challenge_path))
        self.scorer = self.challenge_responder.scorer
        self.model_selector = ModelSelector()

    def init(self):
        data = self.store.load()
        if not self.path.exists():
            data = self.store.save(data)
        return data

    def select_level(self, choice="1"):
        mapping = {"1": "beginner", "2": "intermediate", "3": "experienced"}
        normalized = str(choice).strip().lower()
        reverse = {value: value for value in mapping.values()}
        level = mapping.get(normalized, reverse.get(normalized))
        if level is None:
            raise ValueError("Level must be 1, 2, 3, beginner, intermediate, or experienced")
        data = self.store.load()
        previous_level = data.get("level")
        if previous_level and previous_level != level:
            data.setdefault("path_switches", []).append(
                {
                    "from_level": previous_level,
                    "to_level": level,
                    "timestamp": utc_now(),
                }
            )
        data["level"] = level
        challenge = self._first_available_challenge(data)
        if (
            data.get("current_lesson") is None
            and challenge is not None
            and challenge.lesson_id not in data.get("completed_lessons", [])
        ):
            data["current_lesson"] = challenge.lesson_id
        self.store.save(data)
        return level

    def select_model(self):
        return self.model_selector.select()

    def evaluate_challenge(self, answer, challenge_id=DEFAULT_CHALLENGE_ID, feedback_stage=1):
        outcome = self.challenge_responder.evaluate(challenge_id, answer, feedback_stage)
        challenge = self.challenge_responder.loader.get(challenge_id)
        data = self.store.load()
        data["attempts"] = data.get("attempts", 0) + 1
        if challenge is not None:
            data["current_lesson"] = challenge.lesson_id
            quiz_results = data.setdefault("quiz_results", [])
            quiz_result = next(
                (item for item in quiz_results if item.get("question_id") == challenge_id),
                None,
            )
            if quiz_result is None:
                quiz_result = {"question_id": challenge_id, "score": 0.0, "attempts": 0}
                quiz_results.append(quiz_result)
            quiz_result["attempts"] = quiz_result.get("attempts", 0) + 1
            quiz_result["score"] = max(
                quiz_result.get("score", 0.0),
                1.0 if outcome.accepted else 0.0,
            )
            quiz_result["timestamp"] = utc_now()
        if outcome.accepted and challenge is not None:
            completed = data.setdefault("completed_lessons", [])
            if challenge.lesson_id not in completed:
                completed.append(challenge.lesson_id)
            next_challenge = self._first_available_challenge(data)
            data["current_lesson"] = (
                next_challenge.lesson_id if next_challenge is not None else None
            )
        data.setdefault("timestamps", {})["last_session_at"] = utc_now()
        data = self.store.save(data)
        return outcome, data

    def reveal_solution(self, challenge_id=DEFAULT_CHALLENGE_ID):
        challenge = self.challenge_responder.loader.get(challenge_id)
        if challenge is None or not challenge.accepted_answers:
            return None, self.store.load()
        data = self.store.load()
        revealed = data.setdefault("revealed_lessons", [])
        if challenge.lesson_id not in revealed:
            revealed.append(challenge.lesson_id)
        data["current_lesson"] = challenge.lesson_id
        data.setdefault("timestamps", {})["last_session_at"] = utc_now()
        data = self.store.save(data)
        return challenge.accepted_answers[0], data

    def run_challenge(self, answer):
        """Compatibility wrapper for callers that only consume pass/fail."""
        outcome, data = self.evaluate_challenge(answer)
        return outcome.accepted, data

    def resume(self):
        return self.store.load()

    def get_continue_challenge(self):
        data = self.store.load()
        completed = set(data.get("completed_lessons", []))
        current = self.challenge_responder.loader.get_by_lesson(data.get("current_lesson"))
        if (
            current is not None
            and current.lesson_id not in completed
            and set(current.prerequisites).issubset(completed)
        ):
            return current
        return self._first_available_challenge(data)

    def progress_summary(self):
        data = self.store.load()
        current = self.get_continue_challenge()
        return {
            "level": data.get("level"),
            "completed": len(data.get("completed_lessons", [])),
            "total": len(self.challenge_responder.loader.all()),
            "attempts": data.get("attempts", 0),
            "current_lesson": current.lesson_id if current else None,
        }

    def review_previous(self):
        data = self.store.load()
        for lesson_id in reversed(data.get("completed_lessons", [])):
            challenge = self.challenge_responder.loader.get_by_lesson(lesson_id)
            if challenge is not None:
                return challenge
        return None

    def _first_available_challenge(self, data):
        completed = set(data.get("completed_lessons", []))
        for challenge in self.challenge_responder.loader.all():
            if challenge.lesson_id in completed:
                continue
            if set(challenge.prerequisites).issubset(completed):
                return challenge
        return None


def _show_intro(output):
    output("========================================")
    output("  AI Platform Engineering Learning Tool")
    output("========================================")
    output("A practical path from DevOps/Platform/SRE into MLOps and LLMOps.")
    output("Phases: P0 -> P1 -> P2 -> P3 -> P4 -> P5")


def _run_challenge_interaction(
    session,
    challenge,
    input_fn,
    output,
    *,
    supplied_answer=None,
    non_interactive=False,
):
    try:
        if challenge.challenge_id == DEFAULT_CHALLENGE_ID:
            answer = run_task(
                input_fn=input_fn,
                output=output,
                supplied_answer=supplied_answer,
            )
        else:
            output(f"\n=== {challenge.lesson_id} ===\n")
            output(challenge.prompt)
            answer = capture_answer(
                input_fn=input_fn,
                output=output,
                supplied_answer=supplied_answer,
            )
    except EOFError:
        output("Input ended before the challenge was answered.")
        return 130

    failed_attempts = 0
    remediation_shown = False
    while True:
        if str(answer).strip().casefold() == "show answer":
            solution, _ = session.reveal_solution(challenge.challenge_id)
            if solution is None:
                output("The solution is currently unavailable.")
                return 2
            output(f"Worked solution: {solution}")
            output("This lesson is marked as revealed, not completed. Retry it later to complete it.")
            return 4

        # The answer returned by task_runner is scored in the production path.
        outcome, _ = session.evaluate_challenge(
            answer,
            challenge.challenge_id,
            feedback_stage=failed_attempts + 1,
        )
        if outcome.accepted:
            output("Correct. Progress saved.")
            if outcome.feedback_correct:
                output(f"Why it is correct: {outcome.feedback_correct}")
            return 0

        failed_attempts += 1
        if outcome.reason_code == "empty_answer":
            output("No answer provided. Progress was not completed.")
            if non_interactive:
                return 64
        else:
            output(f"Incorrect. {outcome.reason}")
            if outcome.hint:
                output(f"Hint: {outcome.hint}")
            if non_interactive:
                return 2

        if failed_attempts >= 3 and not remediation_shown:
            if outcome.remediation:
                output(f"Explanation: {outcome.remediation}")
            if outcome.worked_example:
                output(f"Related example: {outcome.worked_example}")
            output("Retry now, or type 'show answer' to reveal this challenge's solution.")
            remediation_shown = True

        try:
            answer = capture_answer(input_fn=input_fn, output=output)
        except EOFError:
            output("Input ended before the challenge was answered.")
            return 130


def _select_level(session, level_choice, output):
    try:
        level = session.select_level(level_choice)
    except ValueError as exc:
        output(str(exc))
        return None
    output(f"Selected level: {level}")
    return level


def _show_progress(session, output):
    progress = session.progress_summary()
    output("Progress:")
    output(f"  Level: {progress['level'] or 'not selected'}")
    output(f"  Lessons completed: {progress['completed']}/{progress['total']}")
    output(f"  Attempts: {progress['attempts']}")
    output(f"  Current lesson: {progress['current_lesson'] or 'all available lessons completed'}")


def _run_menu(session, input_fn, output):
    while True:
        output("\nMain menu:")
        output("  1. Continue")
        output("  2. Show progress")
        output("  3. Select path")
        output("  4. Review previous stage")
        output("  5. Exit")
        try:
            choice = input_fn("Choose an option (1-5): ").strip()
        except EOFError:
            output("Input ended. Exiting without changing progress.")
            return 130

        if choice == "1":
            data = session.resume()
            if data.get("level") is None:
                try:
                    level_choice = input_fn(
                        "Select level (1 beginner, 2 intermediate, 3 experienced): "
                    )
                except EOFError:
                    output("Input ended before a path was selected.")
                    return 130
                if _select_level(session, level_choice, output) is None:
                    continue
            challenge = session.get_continue_challenge()
            if challenge is None:
                output("All currently available lessons are complete.")
                continue
            output(f"Continuing from: {challenge.lesson_id}")
            return _run_challenge_interaction(session, challenge, input_fn, output)

        if choice == "2":
            _show_progress(session, output)
            continue

        if choice == "3":
            try:
                level_choice = input_fn(
                    "Select level (1 beginner, 2 intermediate, 3 experienced): "
                )
            except EOFError:
                output("Input ended before a path was selected.")
                return 130
            _select_level(session, level_choice, output)
            continue

        if choice == "4":
            previous = session.review_previous()
            if previous is None:
                output("No completed stage is available to review yet.")
            else:
                output(f"Previous stage: {previous.lesson_id}")
                output(previous.prompt)
                output(f"Why it worked: {previous.feedback_correct}")
            continue

        if choice == "5":
            output("Goodbye. Your progress is saved.")
            return 0

        output("Invalid option. Choose a number from 1 to 5.")


def run_cli(args, input_fn=input, output=print):
    session = Session(state_path=args.state_path)
    before = session.init()

    _show_intro(output)
    if before.get("level") or before.get("completed_lessons"):
        output(
            f"Resuming previous session: {len(before.get('completed_lessons', []))} lesson(s) completed."
        )

    backend, model = session.select_model()
    output(f"Active local model: {backend}/{model}")

    if not args.non_interactive and args.level is None:
        return _run_menu(session, input_fn, output)

    if args.level is None:
        output("Missing --level in non-interactive mode.")
        return 64
    if _select_level(session, args.level, output) is None:
        return 64
    if args.non_interactive and args.answer is None:
        output("Missing --answer in non-interactive mode.")
        return 64

    challenge = session.challenge_responder.loader.get(DEFAULT_CHALLENGE_ID)
    return _run_challenge_interaction(
        session,
        challenge,
        input_fn,
        output,
        supplied_answer=args.answer,
        non_interactive=args.non_interactive,
    )


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
    except (ProgressLoadError, ProgressSaveError) as exc:
        print(f"Progress could not be loaded or saved: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

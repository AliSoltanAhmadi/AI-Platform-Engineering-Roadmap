import argparse
import json
import subprocess
from pathlib import Path

from session import Session, run_cli


REPO_ROOT = Path(__file__).resolve().parents[2]


def _menu_args(state_path):
    return argparse.Namespace(
        state_path=str(state_path),
        level=None,
        answer=None,
        non_interactive=False,
    )


def _run_menu(state_path, choices):
    stream = iter(choices)
    output = []

    def input_fn(_prompt):
        try:
            return next(stream)
        except StopIteration as exc:
            raise EOFError from exc

    exit_code = run_cli(_menu_args(state_path), input_fn=input_fn, output=output.append)
    return exit_code, "\n".join(output)


def test_main_menu_exposes_all_actions_and_exit(tmp_path):
    exit_code, output = _run_menu(tmp_path / "progress.json", ["5"])

    assert exit_code == 0
    assert "1. Continue" in output
    assert "2. Show progress" in output
    assert "3. Select path" in output
    assert "4. Review previous stage" in output
    assert "5. Exit" in output
    assert "6. Ask a roadmap question" in output
    assert "7. Reset all progress" in output
    assert "8. Take pre/post learning assessment" in output
    assert "Goodbye. Your progress is saved." in output


def test_show_progress_and_review_previous_stage(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()
    session.select_level("beginner")
    session.run_challenge("docker pull nginx")

    exit_code, output = _run_menu(state_path, ["2", "4", "5"])

    assert exit_code == 0
    assert "Lessons completed: 1/2" in output
    assert "Current lesson: run-first-container" in output
    assert "Previous stage: beginner-first-task" in output
    assert "Why it worked:" in output


def test_select_path_preserves_progress_and_records_real_switch(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()
    session.select_level("beginner")
    session.run_challenge("docker pull nginx")

    exit_code, output = _run_menu(state_path, ["3", "2", "2", "5"])
    state = Session(state_path=state_path).resume()

    assert exit_code == 0
    assert "Selected level: intermediate" in output
    assert state["completed_lessons"] == ["beginner-first-task"]
    assert [(item["from_level"], item["to_level"]) for item in state["path_switches"]] == [
        ("beginner", "intermediate")
    ]


def test_next_stage_stays_locked_until_prerequisite_is_complete(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()
    session.select_level("beginner")

    assert session.get_continue_challenge().lesson_id == "beginner-first-task"
    session.run_challenge("banana")
    assert session.get_continue_challenge().lesson_id == "beginner-first-task"
    session.run_challenge("docker pull nginx")
    assert session.get_continue_challenge().lesson_id == "run-first-container"

    exit_code, output = _run_menu(state_path, ["1", "docker run nginx"])
    resumed = Session(state_path=state_path).resume()

    assert exit_code == 0
    assert "Continuing from: run-first-container" in output
    assert resumed["completed_lessons"] == ["beginner-first-task", "run-first-container"]
    assert resumed["current_lesson"] is None


def test_relaunch_continues_last_stage_with_one_menu_selection(tmp_path):
    state_path = tmp_path / "progress.json"
    first = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO_ROOT / "learn.ps1"), "start",
            "-Level", "1", "-Answer", "banana",
            "-StatePath", str(state_path), "-NonInteractive",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert first.returncode == 2

    resumed = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO_ROOT / "learn.ps1"), "start",
            "-StatePath", str(state_path),
        ],
        input="1\ndocker pull nginx\n",
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )

    assert resumed.returncode == 0, resumed.stderr
    assert "Resuming previous session" in resumed.stdout
    assert "Continuing from: beginner-first-task" in resumed.stdout
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["completed_lessons"] == ["beginner-first-task"]
    assert state["current_lesson"] == "run-first-container"

import argparse
import json
import subprocess
from pathlib import Path

from session import Session, run_cli


REPO_ROOT = Path(__file__).resolve().parents[2]


def _interactive_args(state_path):
    return argparse.Namespace(
        state_path=str(state_path),
        level="1",
        non_interactive=False,
        answer=None,
    )


def _run_with_answers(tmp_path, answers):
    state_path = tmp_path / "progress.json"
    answer_stream = iter(answers)
    output = []

    def input_fn(_prompt):
        try:
            return next(answer_stream)
        except StopIteration as exc:
            raise EOFError from exc

    exit_code = run_cli(
        _interactive_args(state_path),
        input_fn=input_fn,
        output=output.append,
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return exit_code, "\n".join(output), state


def test_first_attempt_does_not_reveal_full_solution(tmp_path):
    exit_code, output, state = _run_with_answers(tmp_path, ["show answer"])
    before_reveal = output.split("Worked solution:", 1)[0]

    assert exit_code == 4
    assert "docker pull nginx" not in before_reveal
    assert "podman pull nginx" not in before_reveal
    assert state["attempts"] == 0
    assert state["completed"] == []
    assert state["revealed"] == ["beginner-first-task"]


def test_wrong_then_correct_has_concept_feedback_retry_and_explanation(tmp_path):
    exit_code, output, state = _run_with_answers(
        tmp_path,
        ["docker build nginx", "docker pull nginx"],
    )

    assert exit_code == 0
    assert "operation must download an image" in output
    assert "Build the command from three parts" in output
    assert "Why it is correct:" in output
    assert "targets the requested nginx image" in output
    assert state["attempts"] == 2
    assert state["completed"] == ["beginner-first-task"]
    assert state["revealed"] == []


def test_three_failures_show_remediation_and_related_example_once(tmp_path):
    exit_code, output, state = _run_with_answers(
        tmp_path,
        ["banana", "docker build nginx", "docker pull", "docker pull nginx"],
    )

    assert exit_code == 0
    assert "Explanation: Container image commands" in output
    assert "Related example:" in output
    assert "docker pull alpine" in output
    assert output.count("Related example:") == 1
    assert "type 'show answer'" in output
    assert state["attempts"] == 4
    assert state["completed"] == ["beginner-first-task"]


def test_reveal_is_idempotent_and_does_not_complete(tmp_path):
    state_path = tmp_path / "progress.json"
    session = Session(state_path=state_path)
    session.init()

    solution, first = session.reveal_solution()
    _, second = session.reveal_solution()

    assert solution == "docker pull nginx"
    assert first["completed"] == []
    assert second["revealed"] == ["beginner-first-task"]
    assert second["attempts"] == 0


def test_real_launcher_allows_beginner_to_recover_after_hint(tmp_path):
    state_path = tmp_path / "progress.json"
    result = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO_ROOT / "learn.ps1"), "start",
            "-Level", "1", "-StatePath", str(state_path),
        ],
        input="docker build nginx\ndocker pull nginx\n",
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "operation must download an image" in result.stdout
    assert "Why it is correct:" in result.stdout
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["attempts"] == 2
    assert state["completed"] == ["beginner-first-task"]

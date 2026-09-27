import json
import subprocess
from pathlib import Path


def _run_learn(repo_root, cwd, state_path, answer):
    return subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(repo_root / "learn.ps1"), "start",
            "-Level", "1", "-Answer", answer,
            "-StatePath", str(state_path), "-NonInteractive",
        ],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=10,
    )


def test_session_wrong_then_correct_then_resume(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    state_path = tmp_path / ".local" / "state" / "progress.json"

    wrong = _run_learn(repo_root, tmp_path, state_path, "banana")
    assert wrong.returncode == 2, wrong.stderr
    assert "Incorrect." in wrong.stdout
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["completed"] == []

    correct = _run_learn(repo_root, tmp_path, state_path, "docker pull nginx")
    assert correct.returncode == 0, correct.stderr
    assert "Correct. Progress saved." in correct.stdout
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["completed"] == ["beginner-first-task"]


def test_cli_empty_answer_does_not_complete(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    state_path = tmp_path / ".local" / "state" / "progress.json"

    result = _run_learn(repo_root, tmp_path, state_path, "")
    assert result.returncode == 64, result.stderr
    assert "No answer provided." in result.stdout
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["completed"] == []

    resumed = _run_learn(repo_root, tmp_path, state_path, "docker pull nginx")
    assert resumed.returncode == 0, resumed.stderr
    assert "Resuming previous session" in resumed.stdout
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["completed"] == ["beginner-first-task"]

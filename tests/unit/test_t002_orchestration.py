import json
import subprocess
from pathlib import Path


def _run_learn(repo, cwd, state, answer):
    return subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(repo / "learn.ps1"), "start",
            "-Level", "1", "-Answer", answer,
            "-StatePath", str(state), "-NonInteractive",
        ],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=10,
    )


def test_t002_three_distinguishable_production_results(tmp_path):
    """Empty, wrong, and correct answers have distinct production outcomes."""
    repo = Path(__file__).resolve().parents[2]
    cases = [
        ("empty", "", 64, "No answer provided.", []),
        ("wrong", "banana", 2, "Incorrect.", []),
        ("correct", "docker pull nginx", 0, "Correct. Progress saved.", ["beginner-first-task"]),
    ]

    outcomes = []
    for name, answer, expected_code, expected_message, expected_completed in cases:
        state = tmp_path / name / "progress.json"
        result = _run_learn(repo, tmp_path, state, answer)
        data = json.loads(state.read_text(encoding="utf-8"))

        assert result.returncode == expected_code, result.stderr
        assert expected_message in result.stdout
        assert data["completed_lessons"] == expected_completed
        assert data["attempts"] == 1
        outcomes.append((result.returncode, expected_message, tuple(data["completed_lessons"])))

    assert len(set(outcomes)) == 3

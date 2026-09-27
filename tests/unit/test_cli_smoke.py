import json
import subprocess
from pathlib import Path

from session import Session


def test_module_smoke_import_challenge_scorer():
    from scoring.challenge_scorer import ChallengeScorer

    assert ChallengeScorer is not None


def test_cli_smoke_real_session_init_and_scoring(tmp_path):
    progress = tmp_path / ".local" / "state" / "progress.json"
    session = Session(state_path=str(progress))
    session.init()
    session.select_level("1")

    correct, data = session.run_challenge("banana")
    assert correct is False
    assert "beginner-first-task" not in data["completed_lessons"]

    correct, data = session.run_challenge("docker pull nginx")
    assert correct is True
    assert data["completed_lessons"].count("beginner-first-task") == 1

    resumed = Session(state_path=str(progress)).resume()
    assert resumed["completed_lessons"].count("beginner-first-task") == 1


def test_cli_smoke_powerline_entry_point_fails_on_hang(tmp_path):
    """The real launcher must finish and expose observable success."""
    repo_root = Path(__file__).resolve().parents[2]
    state_path = tmp_path / ".local" / "state" / "progress.json"
    result = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(repo_root / "learn.ps1"), "start",
            "-Level", "1", "-Answer", "docker pull nginx",
            "-StatePath", str(state_path), "-NonInteractive",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "AI Platform Engineering Learning Tool" in result.stdout
    assert "Active local model:" in result.stdout
    assert "Correct. Progress saved." in result.stdout
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["completed_lessons"] == ["beginner-first-task"]

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("powershell")


def test_readme_documents_install_first_run_uninstall_and_state():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for heading in ("## Install", "## First run", "## State, privacy, and reset", "## Uninstall"):
        assert heading in readme
    assert ".\\install.ps1" in readme
    assert "learn start" in readme
    assert ".\\uninstall.ps1" in readme
    assert "progress.json" in readme
    assert "progress.events.jsonl" in readme
    assert "State is deliberately preserved by default" in readme


def test_readme_separates_local_model_paths_and_honest_statuses():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for heading in (
        "### With Ollama",
        "### Without Ollama",
        "### Active",
        "### Experimental",
        "### Planned",
    ):
        assert heading in readme
    assert "Ollama, then vLLM, then the deterministic" in readme
    assert "this is not yet moderated human research" in readme


def test_readme_covers_required_troubleshooting_topics():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for topic in (
        "Python is missing or too old",
        "`learn` is not recognized",
        "Persian text or Unicode symbols look corrupted",
        "Progress cannot be saved (read-only storage)",
    ):
        assert f"### {topic}" in readme


def test_uninstaller_preserves_state_by_default_and_removes_only_on_request(tmp_path):
    install_dir = tmp_path / "bin"
    state_path = tmp_path / "state" / "progress.json"
    event_path = tmp_path / "state" / "progress.events.jsonl"
    command = (
        f". '{REPO_ROOT / 'install.ps1'}' -InstallDir '{install_dir}' -PathScope Process; "
        f"New-Item -ItemType Directory -Path '{state_path.parent}' -Force | Out-Null; "
        f"Set-Content -LiteralPath '{state_path}' -Value '{{}}' -Encoding UTF8; "
        f"Set-Content -LiteralPath '{event_path}' -Value '{{}}' -Encoding UTF8; "
        f". '{REPO_ROOT / 'uninstall.ps1'}' -InstallDir '{install_dir}' -PathScope Process -StatePath '{state_path}'; "
        f"if (-not (Test-Path -LiteralPath '{state_path}')) {{ exit 21 }}; "
        f". '{REPO_ROOT / 'install.ps1'}' -InstallDir '{install_dir}' -PathScope Process; "
        f". '{REPO_ROOT / 'uninstall.ps1'}' -InstallDir '{install_dir}' -PathScope Process -StatePath '{state_path}' -RemoveState; "
        f"if ((Test-Path -LiteralPath '{state_path}') -or (Test-Path -LiteralPath '{event_path}')) {{ exit 22 }}; "
        f". '{REPO_ROOT / 'uninstall.ps1'}' -InstallDir '{install_dir}' -PathScope Process -StatePath '{state_path}'"
    )

    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "Progress was preserved at:" in result.stdout
    assert "Removed local state file:" in result.stdout
    assert "Uninstall complete." in result.stdout
    assert not (install_dir / "learn.cmd").exists()

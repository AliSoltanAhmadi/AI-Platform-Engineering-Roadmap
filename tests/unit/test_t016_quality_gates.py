import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "quality.yml"


def test_repository_schema_validator_passes():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_schemas.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "Schema validation passed" in result.stdout
    assert "cross-file references checked" in result.stdout


def test_ci_workflow_is_valid_yaml_and_enforces_required_commands():
    text = WORKFLOW.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)

    assert isinstance(parsed, dict)
    for command in (
        "python scripts/validate_schemas.py",
        "python -m pytest -q",
        "--cov=src/scoring",
        "--cov-fail-under=90",
        "--cov=src/persist",
        "--cov-fail-under=85",
        ".\\learn.ps1 start",
    ):
        assert command in text


def test_ci_covers_both_windows_shells_and_gates_release_after_e2e():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "shell: powershell" in text
    assert "shell: pwsh" in text
    assert "edition: Desktop" in text
    assert "edition: Core" in text
    assert "if: startsWith(github.ref, 'refs/tags/')" in text
    assert "needs: [quality, windows-shells, end-to-end]" in text
    assert "tests/unit/test_e2e_session_persistence.py" in text
    assert "Compress-Archive" in text
    assert "uninstall.ps1" in text
    assert "if-no-files-found: error" in text


def test_local_quality_gate_matches_ci_coverage_thresholds():
    script = (REPO_ROOT / "scripts" / "quality_gate.ps1").read_text(encoding="utf-8")

    assert "scripts/validate_schemas.py" in script
    assert "--cov=src/scoring" in script and "--cov-fail-under=90" in script
    assert "--cov=src/persist" in script and "--cov-fail-under=85" in script
    assert ".\\learn.ps1 start" in script

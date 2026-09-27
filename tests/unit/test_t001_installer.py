import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("powershell")


def _run_powershell(arguments, *, env=None, cwd=None):
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", *arguments],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd or REPO_ROOT),
        timeout=20,
    )


def test_fresh_powershell_installs_and_runs_learn_commands(tmp_path):
    install_dir = tmp_path / "bin"
    state_path = tmp_path / "state" / "progress.json"
    command = (
        f". '{REPO_ROOT / 'install.ps1'}' -InstallDir '{install_dir}' -PathScope Process; "
        f". '{REPO_ROOT / 'install.ps1'}' -InstallDir '{install_dir}' -PathScope Process; "
        f"$pathMatches = @($env:Path -split ';' | Where-Object {{ $_ -ieq '{install_dir}' }}); "
        "if ($pathMatches.Count -ne 1) { exit 9 }; "
        "learn --help; if ($LASTEXITCODE -ne 0) { exit 10 }; "
        "learn --version; if ($LASTEXITCODE -ne 0) { exit 11 }; "
        f"learn start -Level 1 -Answer 'docker pull nginx' -StatePath '{state_path}' -NonInteractive"
    )

    result = _run_powershell(["-Command", command], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (install_dir / "learn.cmd").is_file()
    assert "Usage: learn start" in result.stdout
    assert "learn 0.1.0" in result.stdout
    assert "AI Platform Engineering Learning Tool" in result.stdout
    assert "Correct. Progress saved." in result.stdout


def test_help_and_version_do_not_require_python(tmp_path):
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)

    for command, expected in [("--help", "Usage:"), ("--version", "learn 0.1.0")]:
        result = _run_powershell(
            ["-File", str(REPO_ROOT / "learn.ps1"), "-Command", command],
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert expected in result.stdout


def test_start_reports_missing_python_with_a_solution(tmp_path):
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)

    result = _run_powershell(
        ["-File", str(REPO_ROOT / "learn.ps1"), "-Command", "start"],
        env=env,
    )

    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "Python was not found" in combined
    assert "Python.Python.3.12" in combined


def test_start_rejects_incompatible_python(tmp_path):
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text("@echo 3.10\n", encoding="ascii")
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)

    result = _run_powershell(
        ["-File", str(REPO_ROOT / "learn.ps1"), "-Command", "start"],
        env=env,
    )

    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "Python 3.10 is incompatible" in combined
    assert "Python 3.11 or newer" in combined

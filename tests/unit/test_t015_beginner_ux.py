import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

from session import run_cli


REPO_ROOT = Path(__file__).resolve().parents[2]


def _args(state_path, *, lang="en", level=None, answer=None, non_interactive=False):
    return argparse.Namespace(
        state_path=str(state_path),
        level=level,
        answer=answer,
        non_interactive=non_interactive,
        lang=lang,
    )


def _interactive(state_path, choices, *, lang="en"):
    values = iter(choices)
    output = []

    def input_fn(_prompt):
        try:
            return next(values)
        except StopIteration as exc:
            raise EOFError from exc

    code = run_cli(_args(state_path, lang=lang), input_fn=input_fn, output=output.append)
    return code, "\n".join(output)


def test_every_entry_screen_gives_a_clear_next_action(tmp_path):
    code, output = _interactive(tmp_path / "progress.json", ["5"])

    assert code == 0
    assert "Next action: choose option 1 to begin" in output
    assert "Next action: enter the number of your chosen option." in output


def test_invalid_choice_explains_what_why_and_recovery(tmp_path):
    code, output = _interactive(tmp_path / "progress.json", ["9", "5"])

    assert code == 0
    assert "What happened? The menu choice is invalid." in output
    assert "Why? The menu accepts only options 1 through 8." in output
    assert "What should I do now? Enter a number from 1 to 8." in output


def test_farsi_ui_has_guidance_and_unicode_without_replacement_characters(tmp_path):
    output = []
    code = run_cli(
        _args(
            tmp_path / "progress.json",
            lang="fa",
            level="1",
            answer="docker pull nginx",
            non_interactive=True,
        ),
        output=output.append,
    )
    rendered = "\n".join(output)

    assert code == 0
    assert "ابزار یادگیری مهندسی پلتفرم هوش مصنوعی" in rendered
    assert "اقدام بعدی" in rendered
    assert "اولین تمرین مبتدی" in rendered
    assert "✓" in rendered
    assert "�" not in rendered


@pytest.mark.parametrize(
    ("persona", "choices", "lang", "expected"),
    [
        ("first-time learner", ["5"], "en", "Next action:"),
        ("learner entering an invalid menu option", ["0", "5"], "en", "What happened?"),
        ("Persian-speaking learner", ["5"], "fa", "اقدام بعدی:"),
    ],
)
def test_three_scripted_novice_personas_can_recover_or_exit(
    tmp_path, persona, choices, lang, expected
):
    code, output = _interactive(tmp_path / f"{lang}-{choices[0]}.json", choices, lang=lang)

    assert code == 0, persona
    assert expected in output


@pytest.mark.parametrize("launcher", ["terminal", "windows-powershell"])
def test_farsi_unicode_survives_supported_windows_launchers(tmp_path, launcher):
    state_path = tmp_path / launcher / "progress.json"
    if launcher == "terminal":
        command = [
            sys.executable,
            str(REPO_ROOT / "src" / "session.py"),
            "start",
            "--level",
            "1",
            "--answer",
            "docker pull nginx",
            "--state-path",
            str(state_path),
            "--lang",
            "fa",
            "--non-interactive",
        ]
    else:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "learn.ps1"),
            "start",
            "-Level",
            "1",
            "-Answer",
            "docker pull nginx",
            "-StatePath",
            str(state_path),
            "-Lang",
            "fa",
            "-NonInteractive",
        ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=env,
        cwd=str(tmp_path),
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "ابزار یادگیری مهندسی پلتفرم هوش مصنوعی" in result.stdout
    assert "✓" in result.stdout
    assert "�" not in result.stdout

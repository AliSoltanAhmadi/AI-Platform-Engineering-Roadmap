import argparse
import json

import pytest

from content.loader import LevelLoader
from session import Session, run_cli


LEVEL_STARTS = {
    "beginner": "challenge-pull-image",
    "intermediate": "challenge-pandas-load",
    "experienced": "challenge-vllm-launch",
}


def test_each_level_has_distinct_start_prerequisites_and_content():
    loader = LevelLoader()

    assert set(loader.levels()) == set(LEVEL_STARTS)
    assert {loader.start_challenge_id(level) for level in loader.levels()} == set(
        LEVEL_STARTS.values()
    )
    for level in loader.levels():
        definition = loader.definition(level)
        assert loader.prerequisites(level)
        assert loader.challenge_ids(level)[0] == LEVEL_STARTS[level]
        for kind in ("lesson", "exercise", "quiz"):
            path = loader.tasks_dir / definition[kind]
            assert path.is_file(), f"{level} is missing its {kind}"
            assert path.read_text(encoding="utf-8").strip()


def test_default_content_paths_work_outside_repository(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    loader = LevelLoader()

    assert "Docker basics" in loader.prerequisites("beginner")
    assert "Intermediate Exercise" in loader.render_level("intermediate")


def test_missing_content_returns_actionable_roadmap_instead_of_dead_end(tmp_path):
    levels_path = tmp_path / "levels.json"
    levels_path.write_text(
        json.dumps(
            {
                "levels": {
                    "beginner": {
                        "prerequisites": [],
                        "lesson": "missing-lesson.md",
                        "exercise": "missing-exercise.md",
                        "quiz": "missing-quiz.md",
                    }
                },
                "glossary": {},
            }
        ),
        encoding="utf-8",
    )
    loader = LevelLoader(levels_path, tmp_path)

    output = loader.render_level("beginner")

    assert "Roadmap overview for beginner" in output
    assert "P0 platform bridge" in output
    assert "Next action:" in output


@pytest.mark.parametrize(
    "term", ["MLOps", "LLMOps", "registry", "inference", "GPU scheduling"]
)
def test_required_glossary_terms_are_defined_before_level_content(term):
    loader = LevelLoader()

    assert not loader.explain_glossary(term).startswith("No definition")
    rendered = loader.render_level("experienced")
    assert rendered.index(f"- {term}:") < rendered.index("--- Lesson ---")


@pytest.mark.parametrize(
    ("level", "lesson_id"),
    [
        ("beginner", "beginner-first-task"),
        ("intermediate", "load-first-dataset"),
        ("experienced", "launch-first-vllm-server"),
    ],
)
def test_session_starts_at_the_challenge_for_the_selected_level(tmp_path, level, lesson_id):
    session = Session(state_path=tmp_path / f"{level}.json")
    session.init()

    session.select_level(level)

    assert session.get_continue_challenge().lesson_id == lesson_id


def test_switching_paths_preserves_history_but_reports_current_path_progress(tmp_path):
    session = Session(state_path=tmp_path / "progress.json")
    session.init()
    session.select_level("beginner")
    session.run_challenge("docker pull nginx")

    session.select_level("experienced")

    state = session.resume()
    summary = session.progress_summary()
    assert state["completed_lessons"] == ["beginner-first-task"]
    assert summary["completed"] == 0
    assert summary["total"] == 1
    assert summary["current_lesson"] == "launch-first-vllm-server"


def test_noninteractive_cli_uses_selected_path_and_shows_learning_material(tmp_path):
    state_path = tmp_path / "progress.json"
    args = argparse.Namespace(
        state_path=str(state_path),
        level="intermediate",
        answer="df = pd.read_csv('file.csv')",
        non_interactive=True,
    )
    output = []

    exit_code = run_cli(args, output=output.append)
    rendered = "\n".join(output)
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert rendered.index("- MLOps:") < rendered.index("--- Lesson ---")
    assert "--- Exercise ---" in rendered
    assert "--- Quiz ---" in rendered
    assert state["completed_lessons"] == ["load-first-dataset"]

import argparse
import json
from pathlib import Path

import pytest

from content.roadmap_explorer import (
    MAX_QUERY_LENGTH,
    KnowledgeBaseLoader,
    RoadmapContentError,
    RoadmapExplorer,
)
from session import run_cli


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pull_image_acceptance_query_maps_to_p0_and_action():
    answer = RoadmapExplorer().ask("چطور یک image را pull کنم؟")

    assert answer.status == "matched"
    assert answer.topic_id == "p0-bridge-docker-compose-fastapi"
    assert answer.phase == "P0 Bridge"
    assert "docker compose" in answer.next_step_action.casefold()


def test_matched_answer_contains_explanation_prerequisites_and_next_step():
    answer = RoadmapExplorer().ask("How do I track a dataset with DVC?")
    rendered = answer.render()

    assert answer.topic_id == "p2-mlops-dvc"
    assert "Phase: P2 Core MLOps" in rendered
    assert "Simple explanation:" in rendered
    assert "Prerequisites:" in rendered
    assert "Next step:" in rendered


def test_out_of_scope_question_is_polite_and_returns_to_menu():
    answer = RoadmapExplorer().ask("What is the weather on Mars tomorrow?")

    assert answer.status == "out_of_scope"
    assert "could not map" in answer.message
    assert "return to the main menu" in answer.message


@pytest.mark.parametrize(
    ("query", "expected_status"),
    [
        ("", "invalid"),
        ("  \n\t  ", "invalid"),
        ("x" * (MAX_QUERY_LENGTH + 1), "too_long"),
    ],
)
def test_empty_multiline_and_long_inputs_are_bounded(query, expected_status):
    answer = RoadmapExplorer().ask(query)

    assert answer.status == expected_status
    assert "main menu" in answer.message


def test_multiline_whitespace_is_sanitized_before_mapping():
    answer = RoadmapExplorer().ask("  How do I\n  pull   an image?  ")

    assert answer.status == "matched"
    assert answer.phase == "P0 Bridge"


def test_menu_answers_question_then_returns_and_can_exit(tmp_path):
    args = argparse.Namespace(
        state_path=str(tmp_path / "progress.json"),
        level=None,
        answer=None,
        non_interactive=False,
    )
    choices = iter(["6", "چطور یک image را pull کنم؟", "5"])
    output = []

    code = run_cli(args, input_fn=lambda _prompt: next(choices), output=output.append)
    rendered = "\n".join(output)

    assert code == 0
    assert "6. Ask a roadmap question" in rendered
    assert "Phase: P0 Bridge" in rendered
    assert "Next step:" in rendered
    assert rendered.count("Main menu:") == 2
    assert "Goodbye. Your progress is saved." in rendered


def test_knowledge_base_schema_errors_are_controlled(tmp_path):
    path = tmp_path / "knowledge.json"
    path.write_text(json.dumps({"schema_version": "1.0.0", "topics": []}), encoding="utf-8")

    with pytest.raises(RoadmapContentError, match="topics"):
        KnowledgeBaseLoader(path).load()


def test_knowledge_base_contract_matches_runtime_schema():
    contract = KnowledgeBaseLoader(REPO_ROOT / "contracts" / "knowledge-base.json").load()

    assert contract["phase_prerequisites"]["DevOps fundamentals"]

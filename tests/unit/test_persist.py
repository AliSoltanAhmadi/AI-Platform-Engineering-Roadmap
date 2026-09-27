import json
from pathlib import Path

import pytest

from persist.progress_store import (
    ProgressLoadError,
    ProgressSaveError,
    ProgressStore,
    SCHEMA_VERSION,
)


REQUIRED_FIELDS = {
    "schema_version",
    "level",
    "completed_lessons",
    "quiz_results",
    "attempts",
    "current_lesson",
    "path_switches",
    "revealed_lessons",
    "timestamps",
}
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_fields_match_progress_contract():
    contract = json.loads(
        (REPO_ROOT / "contracts" / "progress-record.json").read_text(encoding="utf-8")
    )

    assert set(contract["fields"]) == REQUIRED_FIELDS


def test_progress_store_default_matches_contract(temp_state_dir):
    store = ProgressStore(temp_state_dir / "progress.json")
    data = store.load()

    assert set(data) == REQUIRED_FIELDS
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["completed_lessons"] == []
    assert data["quiz_results"] == []
    assert data["attempts"] == 0
    assert data["current_lesson"] is None
    assert data["path_switches"] == []
    assert set(data["timestamps"]) == {"created_at", "updated_at", "last_session_at"}


def test_progress_save_readonly_is_controlled(temp_state_dir, monkeypatch):
    path = temp_state_dir / "readonly.json"
    path.write_text("{}", encoding="utf-8")
    store = ProgressStore(path)
    original_write_text = Path.write_text

    def deny_temp_write(target, *args, **kwargs):
        if target.suffix == ".tmp":
            raise PermissionError("read-only destination")
        return original_write_text(target, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", deny_temp_write)
    with pytest.raises(ProgressSaveError):
        store.save(store.load())
    assert json.loads(path.read_text(encoding="utf-8")) == {}


def test_progress_atomic_write_preserves_previous_state(temp_state_dir, monkeypatch):
    path = temp_state_dir / "atomic.json"
    store = ProgressStore(path)
    old = store.load()
    old["level"] = "beginner"
    store.save(old)

    def fail_replace(*_args, **_kwargs):
        raise OSError("simulated interruption")

    monkeypatch.setattr("persist.progress_store.os.replace", fail_replace)
    changed = store.load()
    changed["level"] = "experienced"
    with pytest.raises(ProgressSaveError):
        store.save(changed)

    assert json.loads(path.read_text(encoding="utf-8"))["level"] == "beginner"
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_same_version_partial_record_is_repaired_and_persisted(temp_state_dir):
    path = temp_state_dir / "partial.json"
    path.write_text('{"schema_version":"1.0.0","level":"beginner"}', encoding="utf-8")

    loaded = ProgressStore(path).load()
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert set(loaded) == REQUIRED_FIELDS
    assert persisted == loaded


@pytest.mark.parametrize("schema_version", ["0.9.0", "1.0.0"])
def test_legacy_aliases_migrate_without_data_loss(temp_state_dir, schema_version):
    path = temp_state_dir / "legacy.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "level": "beginner",
                "completed": ["lesson-1", "lesson-1"],
                "revealed": ["lesson-2"],
                "last_session": "2026-01-01T00:00:00+00:00",
                "attempts": 3,
            }
        ),
        encoding="utf-8",
    )

    loaded = ProgressStore(path).load()

    assert loaded["completed_lessons"] == ["lesson-1"]
    assert loaded["revealed_lessons"] == ["lesson-2"]
    assert loaded["attempts"] == 3
    assert loaded["timestamps"]["last_session_at"] == "2026-01-01T00:00:00+00:00"
    assert "completed" not in loaded
    assert "last_session" not in loaded


def test_readonly_legacy_record_loads_without_being_marked_corrupt(temp_state_dir, monkeypatch):
    path = temp_state_dir / "legacy-readonly.json"
    original = '{"schema_version":"0.9.0","completed":["lesson-1"]}'
    path.write_text(original, encoding="utf-8")
    store = ProgressStore(path)

    def deny_migration(*_args, **_kwargs):
        raise ProgressSaveError("read-only")

    monkeypatch.setattr(store, "save", deny_migration)
    loaded = store.load()

    assert loaded["completed_lessons"] == ["lesson-1"]
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_suffix(path.suffix + ".bad").exists()


def test_future_schema_is_not_downgraded_or_overwritten(temp_state_dir):
    path = temp_state_dir / "future.json"
    original = '{"schema_version":"2.0.0","completed_lessons":["future"]}'
    path.write_text(original, encoding="utf-8")

    with pytest.raises(ProgressLoadError, match="newer than supported"):
        ProgressStore(path).load()

    assert path.read_text(encoding="utf-8") == original


def test_progress_store_graceful_bad_json(temp_state_dir):
    path = temp_state_dir / "bad.json"
    path.write_text("not json", encoding="utf-8")

    result = ProgressStore(path).load()

    assert result["schema_version"] == SCHEMA_VERSION
    assert result["completed_lessons"] == []
    assert path.with_suffix(path.suffix + ".bad").exists()

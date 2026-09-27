import json
from pathlib import Path

import pytest

from persist.progress_store import ProgressSaveError, ProgressStore


def test_progress_save_readonly_is_controlled(temp_state_dir, monkeypatch):
    path = temp_state_dir / "readonly.json"
    path.write_text("{}", encoding="utf-8")
    store = ProgressStore(path=str(path))
    original_write_text = Path.write_text

    def deny_temp_write(target, *args, **kwargs):
        if target.suffix == ".tmp":
            raise PermissionError("read-only destination")
        return original_write_text(target, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", deny_temp_write)
    with pytest.raises(ProgressSaveError):
        store.save({"test": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {}


def test_progress_atomic_write_preserves_previous_state(temp_state_dir, monkeypatch):
    path = temp_state_dir / "atomic.json"
    store = ProgressStore(path=str(path))
    store.save({"version": "1", "data": "old"})

    def fail_replace(*_args, **_kwargs):
        raise OSError("simulated interruption")

    monkeypatch.setattr("persist.progress_store.os.replace", fail_replace)
    with pytest.raises(ProgressSaveError):
        store.save({"version": "2", "data": "new"})

    # Previous state preserved because atomic replace failed; load applies schema defaults
    loaded = store.load()
    assert loaded["schema_version"] == "1.0.0"
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_progress_store_readonly_path_does_not_crash(temp_state_dir):
    path = temp_state_dir / "readonly.json"
    path.write_text("{}", encoding="utf-8")
    store = ProgressStore(path=str(path))
    assert store.load()["schema_version"] == "1.0.0"


def test_progress_store_default_load(temp_state_dir):
    store = ProgressStore(path=str(temp_state_dir / "progress.json"))
    data = store.load()
    assert data["schema_version"] == "1.0.0"
    assert "completed" in data


def test_progress_store_save_and_load(temp_state_dir):
    path = temp_state_dir / "progress.json"
    store = ProgressStore(path=str(path))
    record = {
        "schema_version": "1.0.0",
        "level": "beginner",
        "completed": ["l1"],
        "last_session": "t1",
    }
    store.save(record)
    loaded = store.load()
    assert loaded["level"] == "beginner"
    assert loaded["completed"] == ["l1"]


def test_progress_store_graceful_bad_json(temp_state_dir):
    path = temp_state_dir / "bad.json"
    path.write_text("not json", encoding="utf-8")
    store = ProgressStore(path=str(path))
    result = store.load()
    assert result["schema_version"] == "1.0.0"
    assert result["completed"] == []
    bad_backup = path.with_suffix(path.suffix + ".bad")
    assert bad_backup.exists()

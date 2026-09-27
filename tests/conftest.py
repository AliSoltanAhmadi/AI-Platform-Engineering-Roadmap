import pytest
from pathlib import Path
import sys

# A. Stable imports independent of cwd
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

@pytest.fixture
def temp_state_dir(tmp_path):
    state_dir = tmp_path / ".local" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir

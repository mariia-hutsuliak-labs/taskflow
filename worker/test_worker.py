import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from worker import POLL_INTERVAL_SECONDS  # noqa: E402


def test_poll_interval_is_positive_integer():
    assert isinstance(POLL_INTERVAL_SECONDS, int)
    assert POLL_INTERVAL_SECONDS > 0

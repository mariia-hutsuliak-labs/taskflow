import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent))

from worker import POLL_INTERVAL_SECONDS, check_overdue_tasks  # noqa: E402


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with eng.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE tasks ("
                "id INTEGER PRIMARY KEY, title VARCHAR(200) NOT NULL, "
                "done BOOLEAN NOT NULL DEFAULT 0, due_date DATETIME)"
            )
        )
    return eng


def add_task(engine, title, due_date, done=False):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO tasks (title, done, due_date) VALUES (:t, :d, :due)"),
            {"t": title, "d": done, "due": due_date},
        )


def test_poll_interval_is_positive_integer():
    assert isinstance(POLL_INTERVAL_SECONDS, int)
    assert POLL_INTERVAL_SECONDS > 0


def test_logs_only_overdue_unfinished_tasks(engine, caplog):
    now = datetime.utcnow()
    add_task(engine, "Overdue", now - timedelta(hours=2))
    add_task(engine, "Future", now + timedelta(hours=2))
    add_task(engine, "Done but late", now - timedelta(hours=2), done=True)

    with caplog.at_level(logging.INFO, logger="worker"):
        check_overdue_tasks(engine)

    assert "OVERDUE task" in caplog.text
    assert "'Overdue'" in caplog.text
    assert "Future" not in caplog.text
    assert "Done but late" not in caplog.text


def test_reports_when_nothing_is_overdue(engine, caplog):
    add_task(engine, "Future", datetime.utcnow() + timedelta(days=1))

    with caplog.at_level(logging.INFO, logger="worker"):
        check_overdue_tasks(engine)

    assert "No overdue tasks." in caplog.text

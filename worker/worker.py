"""
Second microservice for the lab: a background worker that periodically
scans the tasks table and logs which tasks are overdue. It intentionally
lives in its own container/process, separate from the API, and talks to
the same PostgreSQL database.
"""
import logging
import os
import time
from datetime import datetime

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
logger = logging.getLogger("worker")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://taskflow:taskflow@db:5432/taskflow",
)
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))


def wait_for_db(engine, retries: int = 15, delay: float = 2.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database is ready.")
            return
        except Exception as exc:  # noqa: BLE001 - simple retry loop for a lab
            logger.info("Database not ready yet (attempt %s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError("Database never became ready")


def check_overdue_tasks(engine) -> None:
    query = text(
        "SELECT id, title, due_date FROM tasks "
        "WHERE done = false AND due_date IS NOT NULL AND due_date < :now"
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"now": datetime.utcnow()}).fetchall()

    if not rows:
        logger.info("No overdue tasks.")
        return

    for row in rows:
        logger.info("OVERDUE task #%s: '%s' (was due %s)", row.id, row.title, row.due_date)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    wait_for_db(engine)
    logger.info("Worker started, polling every %s seconds.", POLL_INTERVAL_SECONDS)
    while True:
        try:
            check_overdue_tasks(engine)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            logger.error("Error while checking tasks: %s", exc)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

from datetime import datetime, timedelta

from app import crud, models


def make_task(done=False, due_date=None):
    return models.Task(
        id=1,
        title="Test task",
        description="",
        done=done,
        due_date=due_date,
        created_at=datetime.utcnow(),
    )


def test_task_without_due_date_is_not_overdue():
    task = make_task(due_date=None)
    assert crud.is_overdue(task) is False


def test_completed_task_is_never_overdue():
    task = make_task(done=True, due_date=datetime.utcnow() - timedelta(days=1))
    assert crud.is_overdue(task) is False


def test_task_with_past_due_date_is_overdue():
    task = make_task(due_date=datetime.utcnow() - timedelta(hours=1))
    assert crud.is_overdue(task) is True


def test_task_with_future_due_date_is_not_overdue():
    task = make_task(due_date=datetime.utcnow() + timedelta(hours=1))
    assert crud.is_overdue(task) is False

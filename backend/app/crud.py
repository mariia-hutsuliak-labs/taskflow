from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models, schemas


def create_task(db: Session, task: schemas.TaskCreate) -> models.Task:
    db_task = models.Task(
        title=task.title,
        description=task.description or "",
        due_date=task.due_date,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task(db: Session, task_id: int) -> Optional[models.Task]:
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def list_tasks(db: Session) -> List[models.Task]:
    return db.query(models.Task).order_by(models.Task.id).all()


def complete_task(db: Session, task_id: int) -> Optional[models.Task]:
    db_task = get_task(db, task_id)
    if db_task is None:
        return None
    db_task.done = True
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int) -> bool:
    db_task = get_task(db, task_id)
    if db_task is None:
        return False
    db.delete(db_task)
    db.commit()
    return True


def is_overdue(task: models.Task, now: Optional[datetime] = None) -> bool:
    """Pure business-logic helper, kept separate so it's trivial to unit test."""
    now = now or datetime.utcnow()
    if task.done or task.due_date is None:
        return False
    return task.due_date < now

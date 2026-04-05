from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from lobesync.db.models import Task, TaskStatus
from typing import List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def create_task(
    session: Session,
    title: str,
    description: str | None = None,
    status: TaskStatus = TaskStatus.PENDING,
    checklist_id: int | None = None,
    deadline: datetime | None = None,
) -> Task | None:
    """
    Creates and persists a new task.

    Args:
        session (Session): Active database session used for persistence.
        title (str): Task title.
        description (str | None): Optional longer description.
        checklist_id (int | None): Optional parent checklist ID to associate the task with.
        deadline (datetime | None): Optional deadline for the task.

    Returns:
        Task | None: The created Task if successful, otherwise None.
    """
    try:
        task = Task(
            title=title,
            description=description,
            status=status,
            checklist_id=checklist_id,
            deadline=deadline,
        )
        session.add(task)
        session.flush()
        session.refresh(task)
        return task
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_task] Failed. Error: {e}")
        return None


def get_all_tasks(session: Session) -> List[Task] | None:
    """
    Retrieves all tasks from the database.

    Args:
        session (Session): Active database session used for querying.

    Returns:
        List[Task] | None: All tasks if any exist, otherwise None.
    """
    try:
        tasks = session.exec(select(Task)).all()
        return tasks or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_all_tasks] Failed. Error: {e}")
        return None


def get_task_by_title(session: Session, title: str) -> Task | None:
    """
    Retrieves the first task whose title contains the given string (case-insensitive).

    Args:
        session (Session): Active database session used for querying.
        title (str): Partial or full title to search for.

    Returns:
        Task | None: The first matching task if found, otherwise None.
    """
    try:
        return session.exec(
            select(Task).where(Task.title.ilike(f"%{title}%"))
        ).first()
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_task_by_title] Failed. Error: {e}")
        return None


def get_task_by_id(session: Session, task_id: int) -> Task | None:
    """
    Retrieves a single task by primary key.

    Args:
        session (Session): Active database session used for querying.
        task_id (int): Primary key of the task.

    Returns:
        Task | None: The task if found, otherwise None.
    """
    try:
        return session.get(Task, task_id)
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_task_by_id] Failed. Error: {e}")
        return None


def get_tasks_by_status(session: Session, status: TaskStatus) -> List[Task] | None:
    """
    Retrieves tasks whose status matches the given value.

    Args:
        session (Session): Active database session used for querying.
        status (TaskStatus): Status value to filter by.

    Returns:
        List[Task] | None: Matching tasks if any, otherwise None.
    """
    try:
        tasks = session.exec(
            select(Task).where(Task.status == status)
        ).all()
        return tasks or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_tasks_by_status] Failed. Error: {e}")
        return None


def get_tasks_by_checklist(session: Session, checklist_id: int) -> List[Task] | None:
    """
    Retrieves all tasks linked to a given checklist.

    Args:
        session (Session): Active database session used for querying.
        checklist_id (int): ID of the checklist.

    Returns:
        List[Task] | None: Tasks for that checklist if any, otherwise None.
    """
    try:
        tasks = session.exec(
            select(Task).where(Task.checklist_id == checklist_id)
        ).all()
        return tasks or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_tasks_by_checklist] Failed. Error: {e}")
        return None


def update_task(
    session: Session,
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    status: TaskStatus | None = None,
    deadline: datetime | None = None,
) -> Task | None:
    """
    Updates optional fields on an existing task. Only arguments that are not None are applied.

    Args:
        session (Session): Active database session used for persistence.
        task_id (int): Primary key of the task to update.
        title (str | None): New title, if provided.
        description (str | None): New description, if provided.
        status (TaskStatus | None): New status, if provided.
        deadline (datetime | None): New deadline, if provided.

    Returns:
        Task | None: The updated task, or None if the task does not exist or the update failed.
    """
    try:
        task = session.get(Task, task_id)
        if not task:
            return None

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if status is not None:
            task.status = status
        if deadline is not None:
            task.deadline = deadline

        task.updated_at = datetime.now()

        session.add(task)
        session.flush()
        session.refresh(task)
        return task

    except SQLAlchemyError as e:
        logger.error(f"[(REPO) update_task] Failed. Error: {e}")
        return None


def delete_task(session: Session, task_id: int) -> bool:
    """
    Deletes a task by primary key.

    Args:
        session (Session): Active database session used for persistence.
        task_id (int): Primary key of the task to delete.

    Returns:
        bool: True if a row was deleted, False if not found or on failure.
    """
    try:
        task = session.get(Task, task_id)
        if not task:
            return False

        session.delete(task)
        session.flush()
        return True

    except SQLAlchemyError as e:
        logger.error(f"[(REPO) delete_task] Failed. Error: {e}")
        return False

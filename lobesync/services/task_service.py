from sqlmodel import Session
import logging
from datetime import datetime

from lobesync.db.repos.task_repo import (
    create_task,
    get_all_tasks,
    get_task_by_id,
    get_task_by_title,
    get_tasks_by_status,
    get_tasks_by_checklist,
    update_task,
    delete_task,
)
from lobesync.db.models import TaskStatus
from lobesync.exceptions.task_exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)


def create_task_service(session: Session, title: str, description: str | None = None, status: TaskStatus = TaskStatus.PENDING, checklist_id: int | None = None, deadline: datetime | None = None):
    """
    Creates a new task.

    Args:
        session (Session): Active database session.
        title (str): Task title.
        description (str | None): Optional longer description.
        status (TaskStatus): Initial status, defaults to PENDING.
        checklist_id (int | None): Optional parent checklist ID.

    Returns:
        Task | None: The created task if successful, otherwise None.
    """
    return create_task(session, title, description, status, checklist_id, deadline)


def get_all_tasks_service(session: Session):
    """
    Retrieves all tasks.

    Args:
        session (Session): Active database session.

    Returns:
        List[Task] | None: All tasks if any exist, otherwise None.
    """
    return get_all_tasks(session)


def get_task_by_title_service(session: Session, title: str):
    """
    Retrieves the first task matching a partial title. Raises if not found.

    Args:
        session (Session): Active database session.
        title (str): Partial or full title to search for.

    Returns:
        Task: The matching task.

    Raises:
        TaskNotFoundError: If no task matches the title.
    """
    task = get_task_by_title(session, title)
    if not task:
        raise TaskNotFoundError(f"No task found matching '{title}'")
    return task


def get_task_service(session: Session, task_id: int):
    """
    Retrieves a task by ID. Raises if not found.

    Args:
        session (Session): Active database session.
        task_id (int): Primary key of the task.

    Returns:
        Task: The task.

    Raises:
        TaskNotFoundError: If no task exists with the given ID.
    """
    task = get_task_by_id(session, task_id)
    if not task:
        raise TaskNotFoundError(f"Task {task_id} not found")
    return task


def get_tasks_by_status_service(session: Session, status: TaskStatus):
    """
    Retrieves all tasks matching a given status.

    Args:
        session (Session): Active database session.
        status (TaskStatus): Status to filter by.

    Returns:
        List[Task] | None: Matching tasks if any, otherwise None.
    """
    return get_tasks_by_status(session, status)


def get_tasks_by_checklist_service(session: Session, checklist_id: int):
    """
    Retrieves all tasks linked to a checklist.

    Args:
        session (Session): Active database session.
        checklist_id (int): ID of the checklist.

    Returns:
        List[Task] | None: Tasks for that checklist if any, otherwise None.
    """
    return get_tasks_by_checklist(session, checklist_id)


def update_task_service(session: Session, task_id: int, title: str | None = None, description: str | None = None, status: TaskStatus | None = None, deadline: datetime | None = None):
    """
    Updates a task's fields. Raises if not found.

    Args:
        session (Session): Active database session.
        task_id (int): Primary key of the task.
        title (str | None): New title, if provided.
        description (str | None): New description, if provided.
        status (TaskStatus | None): New status, if provided.

    Returns:
        Task: The updated task.

    Raises:
        TaskNotFoundError: If no task exists with the given ID.
    """
    task = get_task_by_id(session, task_id)
    if not task:
        raise TaskNotFoundError(f"Task {task_id} not found")
    return update_task(session, task_id, title, description, status, deadline)


def delete_task_service(session: Session, task_id: int):
    """
    Deletes a task. Raises if not found.

    Args:
        session (Session): Active database session.
        task_id (int): Primary key of the task.

    Returns:
        bool: True if deleted successfully.

    Raises:
        TaskNotFoundError: If no task exists with the given ID.
    """
    task = get_task_by_id(session, task_id)
    if not task:
        raise TaskNotFoundError(f"Task {task_id} not found")
    return delete_task(session, task_id)

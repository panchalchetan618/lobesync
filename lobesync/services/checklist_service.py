from sqlmodel import Session
import logging

from lobesync.db.repos.checklist_repo import (
    create_checklist,
    get_checklist_by_id,
    get_all_checklists,
    update_checklist,
    delete_checklist,
    create_checklist_item,
    get_items_by_checklist,
    toggle_checklist_item,
    delete_checklist_item as repo_delete_checklist_item,
)
from lobesync.db.repos.task_repo import get_tasks_by_checklist
from lobesync.db.models import TaskStatus, CheckListItem
from lobesync.exceptions.checklist_exceptions import (
    ChecklistNotFoundError,
    ChecklistItemNotFoundError,
    ChecklistHasPendingTasksError,
)

logger = logging.getLogger(__name__)


def create_checklist_service(session: Session, title: str, description: str | None = None):
    """
    Creates a new checklist.

    Args:
        session (Session): Active database session.
        title (str): Checklist title.
        description (str | None): Optional description.

    Returns:
        CheckList | None: The created checklist if successful, otherwise None.
    """
    return create_checklist(session, title, description)


def get_all_checklists_service(session: Session):
    """
    Retrieves all checklists.

    Args:
        session (Session): Active database session.

    Returns:
        List[CheckList] | None: All checklists if any exist, otherwise None.
    """
    return get_all_checklists(session)


def get_checklist_service(session: Session, checklist_id: int):
    """
    Retrieves a checklist by ID. Raises if not found.

    Args:
        session (Session): Active database session.
        checklist_id (int): Primary key of the checklist.

    Returns:
        CheckList: The checklist.

    Raises:
        ChecklistNotFoundError: If no checklist exists with the given ID.
    """
    checklist = get_checklist_by_id(session, checklist_id)
    if not checklist:
        raise ChecklistNotFoundError(f"Checklist {checklist_id} not found")
    return checklist


def update_checklist_service(session: Session, checklist_id: int, title: str | None = None, description: str | None = None):
    """
    Updates a checklist's title and/or description. Raises if not found.

    Args:
        session (Session): Active database session.
        checklist_id (int): Primary key of the checklist.
        title (str | None): New title, if provided.
        description (str | None): New description, if provided.

    Returns:
        CheckList: The updated checklist.

    Raises:
        ChecklistNotFoundError: If no checklist exists with the given ID.
    """
    checklist = get_checklist_by_id(session, checklist_id)
    if not checklist:
        raise ChecklistNotFoundError(f"Checklist {checklist_id} not found")
    return update_checklist(session, checklist_id, title, description)


def delete_checklist_service(session: Session, checklist_id: int):
    """
    Deletes a checklist. Raises if not found or if pending tasks exist.

    Args:
        session (Session): Active database session.
        checklist_id (int): Primary key of the checklist.

    Returns:
        bool: True if deleted successfully.

    Raises:
        ChecklistNotFoundError: If no checklist exists with the given ID.
        ChecklistHasPendingTasksError: If the checklist has tasks that are not yet done.
    """
    checklist = get_checklist_by_id(session, checklist_id)
    if not checklist:
        raise ChecklistNotFoundError(f"Checklist {checklist_id} not found")

    tasks = get_tasks_by_checklist(session, checklist_id)
    if tasks:
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        if pending:
            raise ChecklistHasPendingTasksError(
                f"Checklist {checklist_id} has {len(pending)} pending task(s). Complete or remove them first."
            )

    return delete_checklist(session, checklist_id)


def create_checklist_item_service(session: Session, checklist_id: int, title: str, description: str | None = None):
    """
    Creates a new item under a checklist. Raises if checklist not found.

    Args:
        session (Session): Active database session.
        checklist_id (int): ID of the parent checklist.
        title (str): Item title.
        description (str | None): Optional item description.

    Returns:
        CheckListItem | None: The created item if successful, otherwise None.

    Raises:
        ChecklistNotFoundError: If the parent checklist does not exist.
    """
    checklist = get_checklist_by_id(session, checklist_id)
    if not checklist:
        raise ChecklistNotFoundError(f"Checklist {checklist_id} not found")
    return create_checklist_item(session, checklist_id, title, description)


def get_checklist_items_service(session: Session, checklist_id: int):
    """
    Retrieves all items for a checklist. Raises if checklist not found.

    Args:
        session (Session): Active database session.
        checklist_id (int): ID of the checklist.

    Returns:
        List[CheckListItem] | None: Items for that checklist if any, otherwise None.

    Raises:
        ChecklistNotFoundError: If the checklist does not exist.
    """
    checklist = get_checklist_by_id(session, checklist_id)
    if not checklist:
        raise ChecklistNotFoundError(f"Checklist {checklist_id} not found")
    return get_items_by_checklist(session, checklist_id)


def toggle_checklist_item_service(session: Session, item_id: int):
    """
    Flips the checked state of a checklist item. Raises if not found.

    Args:
        session (Session): Active database session.
        item_id (int): Primary key of the checklist item.

    Returns:
        CheckListItem: The updated item.

    Raises:
        ChecklistItemNotFoundError: If no item exists with the given ID.
    """
    item = toggle_checklist_item(session, item_id)
    if not item:
        raise ChecklistItemNotFoundError(f"Checklist item {item_id} not found")
    return item


def delete_checklist_item_service(session: Session, item_id: int):
    """
    Deletes a checklist item. Raises if not found.

    Args:
        session (Session): Active database session.
        item_id (int): Primary key of the checklist item.

    Returns:
        bool: True if deleted successfully.

    Raises:
        ChecklistItemNotFoundError: If no item exists with the given ID.
    """
    item = session.get(CheckListItem, item_id)
    if not item:
        raise ChecklistItemNotFoundError(f"Checklist item {item_id} not found")
    return repo_delete_checklist_item(session, item_id)

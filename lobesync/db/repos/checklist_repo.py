from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from lobesync.db.models import CheckList, CheckListItem
from typing import List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def create_checklist(session: Session, title: str, description: str | None = None) -> CheckList | None:
    """
    Creates and persists a new checklist.

    Args:
        session (Session): Active database session used for persistence.
        title (str): Checklist title.
        description (str | None): Optional longer description.

    Returns:
        CheckList | None: The created checklist if successful, otherwise None.
    """
    try:
        checklist = CheckList(title=title, description=description)
        session.add(checklist)
        session.flush()
        session.refresh(checklist)
        return checklist
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_checklist] Failed. Error: {e}")
        return None


def get_all_checklists(session: Session) -> List[CheckList] | None:
    """
    Retrieves all checklists.

    Args:
        session (Session): Active database session used for querying.

    Returns:
        List[CheckList] | None: All checklists if any exist, otherwise None.
    """
    try:
        checklists = session.exec(select(CheckList)).all()
        return checklists or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_all_checklists] Failed. Error: {e}")
        return None


def get_checklist_by_id(session: Session, checklist_id: int) -> CheckList | None:
    """
    Retrieves a checklist by primary key.

    Args:
        session (Session): Active database session used for querying.
        checklist_id (int): Primary key of the checklist.

    Returns:
        CheckList | None: The checklist if found, otherwise None.
    """
    try:
        return session.get(CheckList, checklist_id)
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_checklist_by_id] Failed. Error: {e}")
        return None


def update_checklist(session: Session, checklist_id: int, title: str | None = None, description: str | None = None) -> CheckList | None:
    """
    Updates title and/or description on an existing checklist. Only non-None arguments are applied.

    Args:
        session (Session): Active database session used for persistence.
        checklist_id (int): Primary key of the checklist to update.
        title (str | None): New title, if provided.
        description (str | None): New description, if provided.

    Returns:
        CheckList | None: The updated checklist, or None if not found or on failure.
    """
    try:
        checklist = session.get(CheckList, checklist_id)
        if not checklist:
            return None
        if title is not None:
            checklist.title = title
        if description is not None:
            checklist.description = description
        checklist.updated_at = datetime.now()
        session.add(checklist)
        session.flush()
        session.refresh(checklist)
        return checklist
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) update_checklist] Failed. Error: {e}")
        return None


def delete_checklist(session: Session, checklist_id: int) -> bool:
    """
    Deletes a checklist by primary key.

    Args:
        session (Session): Active database session used for persistence.
        checklist_id (int): Primary key of the checklist to delete.

    Returns:
        bool: True if a row was deleted, False if not found or on failure.
    """
    try:
        checklist = session.get(CheckList, checklist_id)
        if not checklist:
            return False
        session.delete(checklist)
        session.flush()
        return True
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) delete_checklist] Failed. Error: {e}")
        return False


def create_checklist_item(session: Session, checklist_id: int, title: str, description: str | None = None) -> CheckListItem | None:
    """
    Creates and persists a checklist item under a given checklist.

    Args:
        session (Session): Active database session used for persistence.
        checklist_id (int): ID of the parent checklist.
        title (str): Item title.
        description (str | None): Optional item description.

    Returns:
        CheckListItem | None: The created item if successful, otherwise None.
    """
    try:
        item = CheckListItem(checklist_id=checklist_id, title=title, description=description)
        session.add(item)
        session.flush()
        session.refresh(item)
        return item
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_checklist_item] Failed. Error: {e}")
        return None


def get_items_by_checklist(session: Session, checklist_id: int) -> List[CheckListItem] | None:
    """
    Retrieves all items belonging to a checklist.

    Args:
        session (Session): Active database session used for querying.
        checklist_id (int): ID of the checklist.

    Returns:
        List[CheckListItem] | None: Items for that checklist if any, otherwise None.
    """
    try:
        items = session.exec(select(CheckListItem).where(CheckListItem.checklist_id == checklist_id)).all()
        return items or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_items_by_checklist] Failed. Error: {e}")
        return None


def toggle_checklist_item(session: Session, item_id: int) -> CheckListItem | None:
    """
    Flips the checked state of a checklist item and updates its timestamp.

    Args:
        session (Session): Active database session used for persistence.
        item_id (int): Primary key of the checklist item.

    Returns:
        CheckListItem | None: The updated item, or None if not found or on failure.
    """
    try:
        item = session.get(CheckListItem, item_id)
        if not item:
            return None
        item.is_checked = not item.is_checked
        item.updated_at = datetime.now()
        session.add(item)
        session.flush()
        session.refresh(item)
        return item
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) toggle_checklist_item] Failed. Error: {e}")
        return None


def delete_checklist_item(session: Session, item_id: int) -> bool:
    """
    Deletes a checklist item by primary key.

    Args:
        session (Session): Active database session used for persistence.
        item_id (int): Primary key of the item to delete.

    Returns:
        bool: True if a row was deleted, False if not found or on failure.
    """
    try:
        item = session.get(CheckListItem, item_id)
        if not item:
            return False
        session.delete(item)
        session.flush()
        return True
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) delete_checklist_item] Failed. Error: {e}")
        return False

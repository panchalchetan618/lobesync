from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from lobesync.db.models import Note
from typing import List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def create_note(session: Session, title: str, content: str, description: str | None = None) -> Note | None:
    """
    Creates and persists a new note.

    Args:
        session (Session): Active database session used for persistence.
        title (str): Note title.
        content (str): Main note body.
        description (str | None): Optional short description or subtitle.

    Returns:
        Note | None: The created Note if successful, otherwise None.
    """
    try:
        note = Note(title=title, content=content, description=description)
        session.add(note)
        session.flush()
        session.refresh(note)
        return note
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_note] Failed. Error: {e}")
        return None


def get_all_notes(session: Session) -> List[Note] | None:
    """
    Retrieves all notes.

    Args:
        session (Session): Active database session used for querying.

    Returns:
        List[Note] | None: All notes if any exist, otherwise None.
    """
    try:
        notes = session.exec(select(Note)).all()
        return notes or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_all_notes] Failed. Error: {e}")
        return None


def get_note_by_id(session: Session, note_id: int) -> Note | None:
    """
    Retrieves a note by primary key.

    Args:
        session (Session): Active database session used for querying.
        note_id (int): Primary key of the note.

    Returns:
        Note | None: The note if found, otherwise None.
    """
    try:
        return session.get(Note, note_id)
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_note_by_id] Failed. Error: {e}")
        return None


def update_note(session: Session, note_id: int, title: str | None = None, content: str | None = None) -> Note | None:
    """
    Updates title and/or content on an existing note. Only non-None arguments are applied.

    Args:
        session (Session): Active database session used for persistence.
        note_id (int): Primary key of the note to update.
        title (str | None): New title, if provided.
        content (str | None): New body content, if provided.

    Returns:
        Note | None: The updated note, or None if not found or on failure.
    """
    try:
        note = session.get(Note, note_id)
        if not note:
            return None
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        note.updated_at = datetime.now()
        session.add(note)
        session.flush()
        session.refresh(note)
        return note
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) update_note] Failed. Error: {e}")
        return None


def delete_note(session: Session, note_id: int) -> bool:
    """
    Deletes a note by primary key.

    Args:
        session (Session): Active database session used for persistence.
        note_id (int): Primary key of the note to delete.

    Returns:
        bool: True if a row was deleted, False if not found or on failure.
    """
    try:
        note = session.get(Note, note_id)
        if not note:
            return False
        session.delete(note)
        session.flush()
        return True
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) delete_note] Failed. Error: {e}")
        return False

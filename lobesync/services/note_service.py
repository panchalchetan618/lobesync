from sqlmodel import Session
import logging

from lobesync.db.repos.note_repo import (
    create_note,
    get_all_notes,
    get_note_by_id,
    update_note,
    delete_note,
)
from lobesync.exceptions.note_exceptions import NoteNotFoundError

logger = logging.getLogger(__name__)


def create_note_service(session: Session, title: str, content: str, description: str | None = None):
    """
    Creates a new note.

    Args:
        session (Session): Active database session.
        title (str): Note title.
        content (str): Main note body.
        description (str | None): Optional short description.

    Returns:
        Note | None: The created note if successful, otherwise None.
    """
    return create_note(session, title, content, description)


def get_all_notes_service(session: Session):
    """
    Retrieves all notes.

    Args:
        session (Session): Active database session.

    Returns:
        List[Note] | None: All notes if any exist, otherwise None.
    """
    return get_all_notes(session)


def get_note_service(session: Session, note_id: int):
    """
    Retrieves a note by ID. Raises if not found.

    Args:
        session (Session): Active database session.
        note_id (int): Primary key of the note.

    Returns:
        Note: The note.

    Raises:
        NoteNotFoundError: If no note exists with the given ID.
    """
    note = get_note_by_id(session, note_id)
    if not note:
        raise NoteNotFoundError(f"Note {note_id} not found")
    return note


def update_note_service(session: Session, note_id: int, title: str | None = None, content: str | None = None):
    """
    Updates a note's title and/or content. Raises if not found.

    Args:
        session (Session): Active database session.
        note_id (int): Primary key of the note.
        title (str | None): New title, if provided.
        content (str | None): New content, if provided.

    Returns:
        Note: The updated note.

    Raises:
        NoteNotFoundError: If no note exists with the given ID.
    """
    note = get_note_by_id(session, note_id)
    if not note:
        raise NoteNotFoundError(f"Note {note_id} not found")
    return update_note(session, note_id, title, content)


def delete_note_service(session: Session, note_id: int):
    """
    Deletes a note. Raises if not found.

    Args:
        session (Session): Active database session.
        note_id (int): Primary key of the note.

    Returns:
        bool: True if deleted successfully.

    Raises:
        NoteNotFoundError: If no note exists with the given ID.
    """
    note = get_note_by_id(session, note_id)
    if not note:
        raise NoteNotFoundError(f"Note {note_id} not found")
    return delete_note(session, note_id)

from sqlmodel import Session
import logging

from lobesync.db.repos.memory_repo import (
    create_memory,
    get_all_memories,
    get_memory_by_id,
    get_memories_by_type,
    get_memories_by_key,
    get_memories_by_matching_key_or_content,
    update_memory,
    delete_memory,
)
from lobesync.db.models import MEMORY_TYPE
from lobesync.exceptions.memory_exceptions import MemoryNotFoundError

logger = logging.getLogger(__name__)


def create_memory_service(session: Session, key: str, content: str, memory_type: MEMORY_TYPE):
    """
    Creates a new memory entry.

    Args:
        session (Session): Active database session.
        key (str): Identifier for the memory.
        content (str): Memory content.
        memory_type (MEMORY_TYPE): Category of the memory.

    Returns:
        Memory | None: The created memory if successful, otherwise None.
    """
    return create_memory(session, key, content, memory_type)


def upsert_memory_service(session: Session, key: str, content: str, memory_type: MEMORY_TYPE):
    """
    Updates an existing memory by key, or creates it if none exists.
    Preferred write path for the agent to avoid duplicate keys.

    Args:
        session (Session): Active database session.
        key (str): Identifier for the memory.
        content (str): New or initial memory content.
        memory_type (MEMORY_TYPE): Category of the memory.

    Returns:
        Memory | None: The upserted memory if successful, otherwise None.
    """
    existing = get_memories_by_key(session, key)
    if existing:
        return update_memory(session, existing[0].id, content=content, memory_type=memory_type)
    return create_memory(session, key, content, memory_type)


def get_all_memories_service(session: Session):
    """
    Retrieves all memory entries.

    Args:
        session (Session): Active database session.

    Returns:
        List[Memory] | None: All memories if any exist, otherwise None.
    """
    return get_all_memories(session)


def get_memories_by_type_service(session: Session, memory_type: MEMORY_TYPE):
    """
    Retrieves all memories of a given type.

    Args:
        session (Session): Active database session.
        memory_type (MEMORY_TYPE): Type to filter by.

    Returns:
        List[Memory] | None: Matching memories if any, otherwise None.
    """
    return get_memories_by_type(session, memory_type)


def search_memories_service(session: Session, query: str):
    """
    Searches memories by partial match on key or content.

    Args:
        session (Session): Active database session.
        query (str): Search string.

    Returns:
        List[Memory] | None: Matching memories if any, otherwise None.
    """
    return get_memories_by_matching_key_or_content(session, query)


def update_memory_service(session: Session, memory_id: int, content: str | None = None, memory_type: MEMORY_TYPE | None = None):
    """
    Updates a memory's content and/or type. Raises if not found.

    Args:
        session (Session): Active database session.
        memory_id (int): Primary key of the memory.
        content (str | None): New content, if provided.
        memory_type (MEMORY_TYPE | None): New type, if provided.

    Returns:
        Memory: The updated memory.

    Raises:
        MemoryNotFoundError: If no memory exists with the given ID.
    """
    memory = get_memory_by_id(session, memory_id)
    if not memory:
        raise MemoryNotFoundError(f"Memory {memory_id} not found")
    return update_memory(session, memory_id, content, memory_type)


def delete_memory_service(session: Session, memory_id: int):
    """
    Deletes a memory. Raises if not found.

    Args:
        session (Session): Active database session.
        memory_id (int): Primary key of the memory.

    Returns:
        bool: True if deleted successfully.

    Raises:
        MemoryNotFoundError: If no memory exists with the given ID.
    """
    memory = get_memory_by_id(session, memory_id)
    if not memory:
        raise MemoryNotFoundError(f"Memory {memory_id} not found")
    return delete_memory(session, memory_id)

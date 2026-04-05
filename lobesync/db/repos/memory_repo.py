from sqlmodel import Session, select, or_
from sqlalchemy.exc import SQLAlchemyError
from lobesync.db.models import MEMORY_TYPE, Memory
import logging
from typing import List

logger = logging.getLogger(__name__)

def create_memory(session: Session, key: str, content: str, type: MEMORY_TYPE) -> Memory | None:
    """
    Creates and persists a new memory entry.

    Args:
        session (Session): Active database session used for persistence.
        key (str): Unique identifier for the memory entry.
        content (str): The actual data/content to be stored.
        type (MEMORY_TYPE): Category/type of the memory (e.g., short-term, long-term).

    Returns:
        Memory | None: The created Memory object if successful, otherwise None.
    """
    try:
        memory = Memory(key=key, content=content, memory_type=type)
        session.add(memory)
        session.flush()
        session.refresh(memory)
        return memory
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_memory] Failed to create memory. Error: {e}")
        return None

def get_all_memories(session: Session) -> List[Memory] | None:
    """
    Get all memories.

    Args:
        session (Session): Active database session used for persistence.

    Returns:
        List[Memory] | None: List of Memories or None
    """
    try:
        memories = session.exec(select(Memory)).all()
        if not memories:
            return None

        return memories
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_all_memories] Failed to get all memories. Error: {e}")
        return None

def get_memories_by_matching_key_or_content(session: Session, query: str) -> List[Memory] | None:
    """
    Retrieve memory records where either the key or content partially matches the given query.

    Performs a case-insensitive search using SQL `ILIKE`, returning all records where:
    - `Memory.key` contains the query, OR
    - `Memory.content` contains the query.

    Args:
        session (Session): Active database session used for querying.
        query (str): Search string used to match against key and content fields.

    Returns:
        List[Memory] | None: A list of matching Memory objects if found, otherwise None.
    """

    try:
        memories = session.exec(select(Memory).where(or_(Memory.key.ilike(f"%{query}%"), Memory.content.ilike(f"%{query}%")))).all()
        if not memories:
            return None

        return memories
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_memories_by_matching_key_or_content] Failed to get matching key memories. Error: {e}")
        return None

def get_memory_by_id(session: Session, id: int) -> Memory | None:
    """
    Get the exact memory with ID

    Args:
        session (Session): Active database session used for persistence.
        id (int): ID for the memory to get.

    Returns:
        Memory | None: The memory fetched from DB, otherwise None.
    """
    try:
        memory = session.get(Memory, id)
        return memory
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_memory_by_id] Failed to get memory by id. Error: {e}")
        return None


def get_memories_by_type(session: Session, memory_type: MEMORY_TYPE) -> List[Memory] | None:
    """
    Get all memories filtered by type.

    Args:
        session (Session): Active database session.
        memory_type (MEMORY_TYPE): The memory type to filter by.

    Returns:
        List[Memory] | None: Matching memories or None.
    """
    try:
        memories = session.exec(select(Memory).where(Memory.memory_type == memory_type)).all()
        if not memories:
            return None
        return memories
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_memories_by_type] Failed to get memories by type. Error: {e}")
        return None


def get_memories_by_key(session: Session, key: str) -> List[Memory] | None:
    """
    Get all memories with an exact key match.

    Args:
        session (Session): Active database session.
        key (str): The key to look up.

    Returns:
        List[Memory] | None: Matching memories or None.
    """
    try:
        memories = session.exec(select(Memory).where(Memory.key == key)).all()
        if not memories:
            return None
        return memories
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_memories_by_key] Failed to get memories by key. Error: {e}")
        return None


def update_memory(session: Session, id: int, content: str | None = None, memory_type: MEMORY_TYPE | None = None) -> Memory | None:
    """
    Update content and/or type of an existing memory.

    Args:
        session (Session): Active database session.
        id (int): ID of the memory to update.
        content (str | None): New content, if provided.
        memory_type (MEMORY_TYPE | None): New type, if provided.

    Returns:
        Memory | None: Updated memory or None.
    """
    try:
        memory = session.get(Memory, id)
        if not memory:
            return None
        if content is not None:
            memory.content = content
        if memory_type is not None:
            memory.memory_type = memory_type
        from datetime import datetime
        memory.updated_at = datetime.now()
        session.add(memory)
        session.flush()
        session.refresh(memory)
        return memory
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) update_memory] Failed to update memory. Error: {e}")
        return None


def delete_memory(session: Session, id: int) -> bool:
    """
    Delete a memory by ID.

    Args:
        session (Session): Active database session.
        id (int): ID of the memory to delete.

    Returns:
        bool: True if deleted, False otherwise.
    """
    try:
        memory = session.get(Memory, id)
        if not memory:
            return False
        session.delete(memory)
        session.flush()
        return True
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) delete_memory] Failed to delete memory. Error: {e}")
        return False

"""Formatting helpers for the optional cross-session memory context."""

from sqlmodel import Session

from lobesync.config import config
from lobesync.db.repos.memory_repo import get_all_memories


def load_memories_context(session: Session) -> str:
    """Return retained memories for model context when the user opted in."""
    if not config.MEMORY_ENABLED:
        return ""
    memories = get_all_memories(session) or []
    return "\n".join(f"- {memory.key}: {memory.content}" for memory in memories)

from sqlmodel import Session
from datetime import datetime

from lobesync.db.models import TaskStatus, MEMORY_TYPE
from lobesync.services.task_service import (
    create_task_service,
    get_all_tasks_service,
    get_task_service,
    get_task_by_title_service,
    get_tasks_by_status_service,
    get_tasks_by_checklist_service,
    update_task_service,
    delete_task_service,
)
from lobesync.services.checklist_service import (
    create_checklist_service,
    get_all_checklists_service,
    get_checklist_service,
    update_checklist_service,
    delete_checklist_service,
    create_checklist_item_service,
    get_checklist_items_service,
    toggle_checklist_item_service,
    delete_checklist_item_service,
)
from lobesync.services.note_service import (
    create_note_service,
    get_all_notes_service,
    get_note_service,
    update_note_service,
    delete_note_service,
)
from lobesync.services.memory_service import (
    upsert_memory_service,
    get_all_memories_service,
    get_memories_by_type_service,
    search_memories_service,
    update_memory_service,
    delete_memory_service,
)


def _create_task(session: Session, title: str, description: str | None = None, status: str = "pending", checklist_id: int | None = None, deadline: str | None = None):
    deadline_dt = datetime.fromisoformat(deadline) if deadline else None
    return create_task_service(session, title, description, TaskStatus(status), checklist_id, deadline_dt)

def _get_tasks_by_status(session: Session, status: str):
    return get_tasks_by_status_service(session, TaskStatus(status))

def _update_task(session: Session, task_id: int, title: str | None = None, description: str | None = None, status: str | None = None, deadline: str | None = None):
    deadline_dt = datetime.fromisoformat(deadline) if deadline else None
    return update_task_service(session, task_id, title, description, TaskStatus(status) if status else None, deadline_dt)

def _upsert_memory(session: Session, key: str, content: str, memory_type: str = "preference"):
    return upsert_memory_service(session, key, content, MEMORY_TYPE(memory_type))

def _get_memories_by_type(session: Session, memory_type: str):
    return get_memories_by_type_service(session, MEMORY_TYPE(memory_type))

def _update_memory(session: Session, memory_id: int, content: str | None = None, memory_type: str | None = None):
    return update_memory_service(session, memory_id, content, MEMORY_TYPE(memory_type) if memory_type else None)


TOOL_REGISTRY: dict[str, callable] = {
    # Tasks
    "create_task": _create_task,
    "get_all_tasks": lambda session, **_: get_all_tasks_service(session),
    "get_task": lambda session, task_id, **_: get_task_service(session, task_id),
    "get_task_by_title": lambda session, title, **_: get_task_by_title_service(session, title),
    "get_tasks_by_status": _get_tasks_by_status,
    "get_tasks_by_checklist": lambda session, checklist_id, **_: get_tasks_by_checklist_service(session, checklist_id),
    "update_task": _update_task,
    "delete_task": lambda session, task_id, **_: delete_task_service(session, task_id),
    # Checklists
    "create_checklist": lambda session, title, description=None, **_: create_checklist_service(session, title, description),
    "get_all_checklists": lambda session, **_: get_all_checklists_service(session),
    "get_checklist": lambda session, checklist_id, **_: get_checklist_service(session, checklist_id),
    "update_checklist": lambda session, checklist_id, title=None, description=None, **_: update_checklist_service(session, checklist_id, title, description),
    "delete_checklist": lambda session, checklist_id, **_: delete_checklist_service(session, checklist_id),
    "create_checklist_item": lambda session, checklist_id, title, description=None, **_: create_checklist_item_service(session, checklist_id, title, description),
    "get_checklist_items": lambda session, checklist_id, **_: get_checklist_items_service(session, checklist_id),
    "toggle_checklist_item": lambda session, item_id, **_: toggle_checklist_item_service(session, item_id),
    "delete_checklist_item": lambda session, item_id, **_: delete_checklist_item_service(session, item_id),
    # Notes
    "create_note": lambda session, title, content, description=None, **_: create_note_service(session, title, content, description),
    "get_all_notes": lambda session, **_: get_all_notes_service(session),
    "get_note": lambda session, note_id, **_: get_note_service(session, note_id),
    "update_note": lambda session, note_id, title=None, content=None, **_: update_note_service(session, note_id, title, content),
    "delete_note": lambda session, note_id, **_: delete_note_service(session, note_id),
    # Memories
    "upsert_memory": _upsert_memory,
    "get_all_memories": lambda session, **_: get_all_memories_service(session),
    "get_memories_by_type": _get_memories_by_type,
    "search_memories": lambda session, query, **_: search_memories_service(session, query),
    "update_memory": _update_memory,
    "delete_memory": lambda session, memory_id, **_: delete_memory_service(session, memory_id),
}


MAKE_PLAN_TOOL = {
    "name": "make_plan",
    "description": "Create an execution plan for the user's request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "atomic_groups": {
                "type": "array",
                "description": (
                    "List of atomic groups. Each group is a list of steps that must ALL succeed or ALL roll back together. "
                    "Use when one step depends on the result of a previous step in the same group. "
                    "To reference a previous result, use '$tool_name.field' syntax in args "
                    "(e.g. '$create_checklist.id' to use the id returned by create_checklist)."
                ),
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string", "description": "Tool name"},
                            "args": {"type": "object", "description": "Tool arguments. Use '$tool_name.field' for references to previous results."}
                        },
                        "required": ["tool", "args"]
                    }
                }
            },
            "non_atomic": {
                "type": "array",
                "description": "List of independent steps. Each runs in its own transaction. A failure in one does not affect others.",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "description": "Tool name"},
                        "args": {"type": "object", "description": "Tool arguments"}
                    },
                    "required": ["tool", "args"]
                }
            },
        },
        "required": ["atomic_groups", "non_atomic"]
    }
}


PLANNER_SYSTEM_PROMPT = """You are the planning module of Lobesync, a personal AI assistant.

Analyze the user's request and create an execution plan using make_plan.

## Available Tools

### Tasks
- create_task: title (req), description, status (pending/in_progress/completed/cancelled), checklist_id, deadline (ISO datetime string e.g. 2026-04-10T17:00:00)
- get_all_tasks: no args
- get_task: task_id
- get_task_by_title: title (partial match) — use this when you know the name but not the ID. Chain with update_task or delete_task in an atomic group using '$get_task_by_title.id'
- get_tasks_by_status: status
- get_tasks_by_checklist: checklist_id
- update_task: task_id (req), title, description, status, deadline (ISO datetime string)
- delete_task: task_id

### Checklists
- create_checklist: title (req), description
- get_all_checklists: no args
- get_checklist: checklist_id
- update_checklist: checklist_id (req), title, description
- delete_checklist: checklist_id
- create_checklist_item: checklist_id (req), title (req), description
- get_checklist_items: checklist_id
- toggle_checklist_item: item_id
- delete_checklist_item: item_id

### Notes
- create_note: title (req), content (req), description
- get_all_notes: no args
- get_note: note_id
- update_note: note_id (req), title, content
- delete_note: note_id

### Memories
- upsert_memory: key (req), content (req), memory_type (preference/goal/achievement/learning/emotional)
- get_all_memories: no args
- get_memories_by_type: memory_type
- search_memories: query
- update_memory: memory_id (req), content, memory_type
- delete_memory: memory_id

## Planning Rules

**atomic_groups**: Use when steps depend on each other. All steps in a group succeed or all roll back.
- Reference earlier results with '$tool_name.field' (e.g. '$create_checklist.id')
- Example: create_checklist then create_task with checklist_id = '$create_checklist.id'

**non_atomic**: Use for independent operations. Each runs separately.
- Example: create a note AND update an unrelated task status

**CRITICAL RULE**: You MUST call make_plan for ANY operation that creates, reads, updates, or deletes data. NEVER respond with text claiming you performed an action without calling make_plan first. If you say "I created your task" or "I marked it in progress" without calling make_plan, that is a hallucination — the action did not happen.

**No tools needed**: ONLY respond in plain text (without calling make_plan) when the user is purely chatting, greeting, or asking a general question that requires absolutely no data access.

## Proactive Memory
When the user shares personal information about themselves — preferences, goals, skills, achievements, feelings, or habits — automatically include upsert_memory in your plan even if they did not ask you to remember it. Choose the appropriate memory_type:
- preference: likes, dislikes, settings, working style
- goal: aspirations, targets, plans
- achievement: accomplishments, completed milestones
- learning: new skills, knowledge, things they are studying
- emotional: feelings, moods, emotional states

Use a short descriptive key (e.g. "preferred_language", "career_goal", "current_mood").
"""

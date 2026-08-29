"""Deterministic rendering of completed tool operations.

The executor already has authoritative results. Formatting them locally keeps
completion messages reliable, auditable, and free of a second LLM request.
"""

from lobesync.agent.state import AgentState


def _item_label(result: object) -> str:
    if not isinstance(result, dict):
        return ""
    title = result.get("title") or result.get("key")
    identifier = result.get("id")
    details = f' "{title}"' if title else ""
    if identifier is not None:
        details += f" (ID: {identifier})"
    return details


def _format_success(tool_name: str, result: object) -> str:
    action, _, subject = tool_name.partition("_")
    subject = subject.replace("_", " ")
    if action == "get":
        if isinstance(result, list):
            return f"Retrieved {len(result)} {subject} item(s)."
        return f"Retrieved {subject}{_item_label(result)}."
    if action == "create":
        return f"Created {subject}{_item_label(result)}."
    if action == "update":
        return f"Updated {subject}{_item_label(result)}."
    if action == "delete":
        return f"Deleted {subject}."
    if action == "toggle":
        return f"Updated {subject}{_item_label(result)}."
    if action == "upsert":
        return f"Saved {subject}{_item_label(result)}."
    if action == "search":
        count = len(result) if isinstance(result, list) else 0
        return f"Found {count} matching {subject} item(s)."
    return f"Completed {tool_name.replace('_', ' ')}."


def completion_node(state: AgentState) -> dict:
    """Create a response from authoritative execution results."""
    lines = []
    for result in state.get("execution_results") or []:
        if result["error"]:
            lines.append(f"Could not {result['tool'].replace('_', ' ')}: {result['error']}.")
        else:
            lines.append(_format_success(result["tool"], result["result"]))
    return {"final_response": "\n".join(lines) or "No changes were made."}

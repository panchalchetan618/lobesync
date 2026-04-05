import logging
from sqlmodel import Session

from lobesync.db.database import engine
from lobesync.agent.state import AgentState
from lobesync.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


def _serialize_result(result) -> dict | list | bool | str | None:
    """Convert SQLModel objects to plain dicts for storage in state."""
    if result is None or isinstance(result, bool):
        return result
    if isinstance(result, list):
        return [_serialize_result(r) for r in result]
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return str(result)


def _resolve_args(args: dict, context: dict) -> dict:
    """
    Replace '$tool_name.field' references in args with actual values from atomic_context.

    Raises:
        ValueError: If a reference cannot be resolved.
    """
    resolved = {}
    for key, value in args.items():
        if isinstance(value, str) and value.startswith("$"):
            ref = value[1:]
            parts = ref.split(".", 1)
            tool_name = parts[0]
            field = parts[1] if len(parts) > 1 else None

            if tool_name not in context:
                raise ValueError(f"Cannot resolve '{value}': '{tool_name}' has not been executed yet in this group")

            result = context[tool_name]
            if field is None:
                resolved[key] = result
            elif hasattr(result, field):
                resolved[key] = getattr(result, field)
            elif isinstance(result, dict) and field in result:
                resolved[key] = result[field]
            else:
                raise ValueError(f"Cannot resolve '{value}': field '{field}' not found on result")
        else:
            resolved[key] = value
    return resolved


def executor_node(state: AgentState) -> dict:
    """
    Executes the plan produced by the planner.

    - atomic_groups: each group runs in a single session. Any failure rolls back the whole group.
    - non_atomic: each step runs in its own session. Failures are isolated.
    """
    plan = state["plan"] or {}
    execution_results: list[dict] = []

    for group_idx, group in enumerate(plan.get("atomic_groups", [])):
        group_results = []
        with Session(engine) as session:
            atomic_context: dict = {}
            try:
                for step in group:
                    tool_name = step["tool"]
                    args = step.get("args", {})

                    if tool_name not in TOOL_REGISTRY:
                        raise ValueError(f"Unknown tool: '{tool_name}'")

                    resolved = _resolve_args(args, atomic_context)
                    result = TOOL_REGISTRY[tool_name](session, **resolved)
                    serialized = _serialize_result(result)  # must happen before commit
                    atomic_context[tool_name] = result

                    group_results.append({
                        "tool": tool_name,
                        "args": args,
                        "result": serialized,
                        "error": None,
                    })

                session.commit()
                execution_results.extend(group_results)
                logger.info(f"Atomic group {group_idx} committed ({len(group)} steps)")

            except Exception as e:
                session.rollback()
                logger.error(f"Atomic group {group_idx} failed and rolled back: {e}")
                for step in group:
                    execution_results.append({
                        "tool": step["tool"],
                        "args": step.get("args", {}),
                        "result": None,
                        "error": str(e),
                    })

    for step in plan.get("non_atomic", []):
        tool_name = step["tool"]
        args = step.get("args", {})

        with Session(engine) as session:
            try:
                if tool_name not in TOOL_REGISTRY:
                    raise ValueError(f"Unknown tool: '{tool_name}'")

                result = TOOL_REGISTRY[tool_name](session, **args)
                serialized = _serialize_result(result)  # must happen before commit
                session.commit()

                execution_results.append({
                    "tool": tool_name,
                    "args": args,
                    "result": serialized,
                    "error": None,
                })
                logger.info(f"Non-atomic step '{tool_name}' committed")

            except Exception as e:
                session.rollback()
                logger.error(f"Non-atomic step '{tool_name}' failed: {e}")
                execution_results.append({
                    "tool": tool_name,
                    "args": args,
                    "result": None,
                    "error": str(e),
                })

    return {"execution_results": execution_results}

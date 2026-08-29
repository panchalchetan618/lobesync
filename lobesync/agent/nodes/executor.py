import logging

from sqlmodel import Session

from lobesync.agent.state import AgentState
from lobesync.agent.tools import TOOL_REGISTRY
from lobesync.db.database import get_engine

logger = logging.getLogger(__name__)


def _requires_bulk_delete_confirmation(plan: dict) -> bool:
    delete_count = 0
    for group in plan.get("atomic_groups", []):
        if isinstance(group, list):
            delete_count += sum(
                1
                for step in group
                if isinstance(step, dict) and str(step.get("tool", "")).startswith("delete_")
            )
    delete_count += sum(
        1
        for step in plan.get("non_atomic", [])
        if isinstance(step, dict) and str(step.get("tool", "")).startswith("delete_")
    )
    return delete_count > 1


def _require_authoritative_result(tool_name: str, result: object) -> None:
    """Reject write operations that did not return a verified result."""
    if tool_name.startswith(("create_", "update_", "upsert_", "toggle_")) and result is None:
        raise RuntimeError(f"{tool_name} did not return a result")
    if tool_name.startswith("delete_") and result is not True:
        raise RuntimeError(f"{tool_name} was not completed")


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
                raise ValueError(
                    f"Cannot resolve '{value}': '{tool_name}' has not been executed yet in this group"
                )

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


def _validate_step(step: object) -> tuple[str, str, dict]:
    """Validate untrusted model output before invoking an application tool."""
    if not isinstance(step, dict):
        raise ValueError("Plan step must be an object")
    tool_name = step.get("tool")
    step_id = step.get("id", tool_name)
    args = step.get("args", {})
    if not isinstance(tool_name, str) or tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name!r}")
    if not isinstance(step_id, str) or not step_id:
        raise ValueError("Plan step id must be a non-empty string")
    if not isinstance(args, dict):
        raise ValueError(f"Arguments for '{step_id}' must be an object")
    return step_id, tool_name, args


def executor_node(state: AgentState) -> dict:
    """
    Executes the plan produced by the planner.

    - atomic_groups: each group runs in a single session. Any failure rolls back the whole group.
    - non_atomic: each step runs in its own session. Failures are isolated.
    """
    plan = state["plan"] or {}
    if not isinstance(plan, dict):
        return {
            "execution_results": [
                {
                    "step_id": "plan",
                    "tool": "plan",
                    "args": {},
                    "result": None,
                    "error": "Plan must be an object",
                }
            ]
        }

    if _requires_bulk_delete_confirmation(plan) and not state.get("approved_bulk_plan"):
        return {
            "execution_results": [
                {
                    "step_id": "bulk_delete",
                    "tool": "bulk_delete",
                    "args": {},
                    "result": None,
                    "error": "Confirmation required. Choose Yes to delete all selected items.",
                }
            ],
            "bulk_delete_confirmation_required": True,
        }
    execution_results: list[dict] = []

    for group_idx, group in enumerate(plan.get("atomic_groups", [])):
        group_results = []
        with Session(get_engine()) as session:
            atomic_context: dict = {}
            try:
                for step in group:
                    step_id, tool_name, atomic_args = _validate_step(step)
                    if step_id in atomic_context:
                        raise ValueError(f"Duplicate step id in atomic group: '{step_id}'")

                    resolved = _resolve_args(atomic_args, atomic_context)
                    result = TOOL_REGISTRY[tool_name](session, **resolved)
                    _require_authoritative_result(tool_name, result)
                    serialized = _serialize_result(result)  # must happen before commit
                    atomic_context[step_id] = result

                    group_results.append(
                        {
                            "step_id": step_id,
                            "tool": tool_name,
                            "args": resolved,
                            "result": serialized,
                            "error": None,
                        }
                    )

                session.commit()
                execution_results.extend(group_results)
                logger.info(f"Atomic group {group_idx} committed ({len(group)} steps)")

            except Exception as e:
                session.rollback()
                logger.error(f"Atomic group {group_idx} failed and rolled back: {e}")
                for step in group:
                    failed_step = step if isinstance(step, dict) else {}
                    execution_results.append(
                        {
                            "step_id": failed_step.get("id", failed_step.get("tool", "unknown")),
                            "tool": failed_step.get("tool", "unknown"),
                            "args": failed_step.get("args", {}),
                            "result": None,
                            "error": str(e),
                        }
                    )

    for step in plan.get("non_atomic", []):
        with Session(get_engine()) as session:
            args: dict = {}
            try:
                step_id, tool_name, args = _validate_step(step)

                result = TOOL_REGISTRY[tool_name](session, **args)
                _require_authoritative_result(tool_name, result)
                serialized = _serialize_result(result)  # must happen before commit
                session.commit()

                execution_results.append(
                    {
                        "step_id": step_id,
                        "tool": tool_name,
                        "args": args,
                        "result": serialized,
                        "error": None,
                    }
                )
                logger.info(f"Non-atomic step '{tool_name}' committed")

            except Exception as e:
                session.rollback()
                tool_name = step.get("tool", "unknown") if isinstance(step, dict) else "unknown"
                logger.error(f"Non-atomic step '{tool_name}' failed: {e}")
                execution_results.append(
                    {
                        "step_id": step.get("id", tool_name)
                        if isinstance(step, dict)
                        else "unknown",
                        "tool": tool_name,
                        "args": args,
                        "result": None,
                        "error": str(e),
                    }
                )

    return {"execution_results": execution_results}

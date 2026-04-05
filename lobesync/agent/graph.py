from langgraph.graph import StateGraph, START, END

from lobesync.agent.state import AgentState
from lobesync.agent.nodes.planner import planner_node
from lobesync.agent.nodes.executor import executor_node
from lobesync.agent.nodes.completion import completion_node
from lobesync.agent.nodes.commitment import commitment_node


def _route_after_planner(state: AgentState) -> str:
    if state.get("final_response"):
        return "commitment"
    plan = state.get("plan") or {}
    has_work = bool(plan.get("atomic_groups")) or bool(plan.get("non_atomic"))
    return "executor" if has_work else "completion"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("completion", completion_node)
    graph.add_node("commitment", commitment_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {
            "executor": "executor",
            "completion": "completion",
            "commitment": "commitment",
        },
    )
    graph.add_edge("executor", "completion")
    graph.add_edge("completion", "commitment")
    graph.add_edge("commitment", END)

    return graph.compile()

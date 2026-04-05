from typing import TypedDict


class AgentState(TypedDict):
    user_query: str
    chat_session_id: int
    memories_context: str
    plan: dict | None
    execution_results: list[dict]
    final_response: str | None
    input_tokens: int
    output_tokens: int
    model_name: str | None
    error: str | None

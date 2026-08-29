from typing import NotRequired, TypedDict


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
    approved_bulk_plan: NotRequired[dict | None]
    bulk_delete_confirmation_required: NotRequired[bool]

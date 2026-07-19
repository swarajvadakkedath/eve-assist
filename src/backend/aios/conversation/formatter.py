"""Response formatting for frontend delivery."""

from typing import Any

from aios.conversation.models import Message, ToolCall, ToolCallStatus, StreamEvent, StreamEventType


def format_conversation_response(conversation: Any) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else "",
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else "",
        "active_project": conversation.active_project,
        "message_count": conversation.message_count,
        "is_active": conversation.is_active,
        "is_branch": conversation.is_branch if hasattr(conversation, "is_branch") else False,
        "parent_id": conversation.parent_id if hasattr(conversation, "parent_id") else None,
        "title_is_custom": conversation.title_is_custom if hasattr(conversation, "title_is_custom") else False,
        "metadata": conversation.metadata,
    }


def format_message_response(message: Message, include_tool_details: bool = False) -> dict:
    response = {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role.value if hasattr(message.role, "value") else message.role,
        "content": message.content,
        "timestamp": message.timestamp.isoformat() if message.timestamp else "",
        "tokens_used": message.tokens_used,
        "attachments": message.attachments,
        "metadata": message.metadata,
        "is_regenerated": message.is_regenerated,
        "latency_ms": message.latency_ms,
    }

    if include_tool_details and message.tool_calls:
        response["tool_calls"] = [
            {
                "tool_name": tc.tool_name,
                "capability": tc.capability,
                "parameters": tc.parameters,
                "status": tc.status.value if hasattr(tc.status, "value") else tc.status,
                "execution_time": tc.execution_time,
                "result": tc.result,
            }
            for tc in message.tool_calls
        ]

    if message.edit_history:
        response["edit_history"] = [
            {
                "original_content": e.original_content,
                "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
                "regenerated": e.regenerated,
            }
            for e in message.edit_history
        ]

    return response


def format_message_list(messages: list[Message], include_tool_details: bool = False) -> list[dict]:
    return [format_message_response(m, include_tool_details) for m in messages]


def format_tool_call_card(tc: ToolCall) -> dict:
    return {
        "tool_name": tc.tool_name,
        "capability": tc.capability,
        "parameters": tc.parameters,
        "status": tc.status.value if hasattr(tc.status, "value") else tc.status,
        "execution_time": tc.execution_time,
        "result": tc.result,
    }


def create_token_event(token: str) -> dict:
    return {"type": StreamEventType.TOKEN.value, "data": {"token": token}}


def create_done_event(message_id: str, tokens_used: int = 0) -> dict:
    return {"type": StreamEventType.DONE.value, "data": {"message_id": message_id, "tokens_used": tokens_used}}


def create_error_event(error: str, recoverable: bool = True) -> dict:
    return {"type": StreamEventType.ERROR.value, "data": {"error": error, "recoverable": recoverable}}


def create_tool_call_event(tool_name: str, capability: str, parameters: dict) -> dict:
    return {
        "type": StreamEventType.TOOL_CALL.value,
        "data": {"tool_name": tool_name, "capability": capability, "parameters": parameters},
    }


def create_tool_result_event(tool_name: str, result: Any, success: bool) -> dict:
    return {
        "type": StreamEventType.TOOL_RESULT.value,
        "data": {"tool_name": tool_name, "result": result, "success": success},
    }


def create_status_event(status: str, message: str = "") -> dict:
    return {"type": StreamEventType.STATUS.value, "data": {"status": status, "message": message}}


def create_planner_started_event(request: str) -> dict:
    return {"type": StreamEventType.PLANNER_STARTED.value, "data": {"request": request}}


def create_planner_completed_event(steps: int) -> dict:
    return {"type": StreamEventType.PLANNER_COMPLETED.value, "data": {"steps": steps}}


def create_memory_retrieval_event(query: str, count: int) -> dict:
    return {"type": StreamEventType.MEMORY_RETRIEVAL.value, "data": {"query": query, "count": count}}


def create_tool_requested_event(tool_name: str, capability: str) -> dict:
    return {"type": StreamEventType.TOOL_REQUESTED.value, "data": {"tool_name": tool_name, "capability": capability}}


def create_tool_running_event(tool_name: str) -> dict:
    return {"type": StreamEventType.TOOL_RUNNING.value, "data": {"tool_name": tool_name}}


def create_tool_completed_event(tool_name: str, success: bool, duration: float) -> dict:
    return {
        "type": StreamEventType.TOOL_COMPLETED.value,
        "data": {"tool_name": tool_name, "success": success, "duration": duration},
    }


def create_context_loaded_event(context_size: int) -> dict:
    return {"type": StreamEventType.CONTEXT_LOADED.value, "data": {"context_size": context_size}}


def create_final_response_event() -> dict:
    return {"type": StreamEventType.FINAL_RESPONSE.value, "data": {}}


def create_title_generated_event(title: str) -> dict:
    return {"type": StreamEventType.TITLE_GENERATED.value, "data": {"title": title}}


def create_analytics_event(analytics: dict) -> dict:
    return {"type": StreamEventType.ANALYTICS.value, "data": analytics}


def create_vision_observation_event(observation: dict) -> dict:
    return {"type": StreamEventType.VISION_OBSERVATION.value, "data": observation}

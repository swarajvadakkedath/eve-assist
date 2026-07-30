"""Chat API routes — uses ConversationService for all operations."""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
import json

import structlog

from aios.utils.tracer import trace_async, trace_async_gen
from aios.conversation.models import Conversation, Message, StreamEventType
from aios.conversation.exceptions import ConversationNotFoundError, AIProviderError
from aios.conversation.formatter import format_conversation_response, format_message_response, format_message_list

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["chat"])


class MessageRequest(BaseModel):
    conversation_id: str | None = None
    content: str
    stream: bool = False
    provider_id: str | None = None
    model_id: str | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content cannot be empty")
        if len(v) > 100000:
            raise ValueError(f"content exceeds 100000 characters ({len(v)})")
        return v


class StreamRequest(BaseModel):
    conversation_id: str
    content: str
    provider_id: str | None = None
    model_id: str | None = None


@router.post("/chat/conversation")
async def create_conversation(req: Request, title: str | None = None, project: str | None = None):
    cs = req.app.state.conversation_service
    conv = await cs.create_conversation(title=title, project=project)
    return format_conversation_response(conv)


@router.get("/chat/conversations")
async def list_conversations(req: Request, limit: int = 50, offset: int = 0):
    cs = req.app.state.conversation_service
    convs = await cs.list_conversations(limit=limit, offset=offset)
    return {"conversations": [format_conversation_response(c) for c in convs]}


@router.get("/chat/conversation/{conversation_id}")
async def get_conversation(req: Request, conversation_id: str):
    cs = req.app.state.conversation_service
    try:
        conv = await cs.get_conversation(conversation_id)
        return format_conversation_response(conv)
    except ConversationNotFoundError as e:
        return {"error": str(e)}, 404


class UpdateConversationRequest(BaseModel):
    title: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    routing_policy: str | None = None


@router.put("/chat/conversation/{conversation_id}")
async def update_conversation(req: Request, conversation_id: str, body: UpdateConversationRequest | None = None):
    cs = req.app.state.conversation_service
    try:
        if body and body.title:
            conv = await cs.rename_conversation(conversation_id, body.title)
        else:
            conv = await cs.get_conversation(conversation_id)
        if body and (body.provider_id is not None or body.model_id is not None or body.routing_policy is not None):
            conv = await cs.set_provider_model(
                conversation_id,
                body.provider_id,
                body.model_id,
                routing_policy=body.routing_policy,
            )
        return format_conversation_response(conv)
    except ConversationNotFoundError as e:
        return {"error": str(e)}, 404


@router.delete("/chat/conversation/{conversation_id}")
async def delete_conversation(req: Request, conversation_id: str):
    cs = req.app.state.conversation_service
    try:
        await cs.delete_conversation(conversation_id)
        return {"status": "deleted"}
    except ConversationNotFoundError as e:
        return {"error": str(e)}, 404


@router.post("/chat/message")
async def send_message(req: Request, body: MessageRequest):
    cs = req.app.state.conversation_service
    try:
        if not body.conversation_id:
            conv = await cs.create_conversation(provider_id=body.provider_id, model_id=body.model_id)
            body.conversation_id = conv.id
        elif body.provider_id or body.model_id:
            await cs.set_provider_model(body.conversation_id, body.provider_id, body.model_id)

        msg = await cs.send_message(body.conversation_id, body.content)
        return {
            "conversation_id": msg.conversation_id,
            "message_id": msg.id,
            "content": msg.content,
            "role": msg.role.value if hasattr(msg.role, "value") else msg.role,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else "",
            "tokens_used": msg.tokens_used,
        }
    except ConversationNotFoundError as e:
        return {"error": str(e)}, 404
    except AIProviderError as e:
        return {"error": str(e)}, 503


@router.post("/chat/stream")
@trace_async
async def stream_message(req: Request, body: StreamRequest):
    cs = req.app.state.conversation_service

    if body.provider_id or body.model_id:
        await cs.set_provider_model(body.conversation_id, body.provider_id, body.model_id)

    @trace_async_gen
    async def event_generator():
        async for event in cs.stream_message(body.conversation_id, body.content):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/history/{conversation_id}")
async def get_history(req: Request, conversation_id: str, limit: int = 100, offset: int = 0):
    cs = req.app.state.conversation_service
    try:
        messages = await cs.get_history(conversation_id, limit=limit, offset=offset)
        return {"messages": format_message_list(messages, include_tool_details=True)}
    except ConversationNotFoundError as e:
        return {"error": str(e)}, 404


@router.delete("/chat/history/{conversation_id}")
async def clear_history(req: Request, conversation_id: str):
    cs = req.app.state.conversation_service
    try:
        await cs.clear_history(conversation_id)
        return {"status": "cleared"}
    except ConversationNotFoundError as e:
        return {"error": str(e)}, 404

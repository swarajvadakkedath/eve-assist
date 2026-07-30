"""Tests for Conversation model snapshot — provider_id, model_id persistence."""

from datetime import datetime, timezone
from aios.conversation.models import Conversation, Message, MessageRole


def test_conversation_defaults():
    c = Conversation()
    assert c.provider_id is None
    assert c.model_id is None
    assert c.temperature is None
    assert c.top_p is None
    assert c.max_tokens is None
    assert c.streaming_enabled is True
    assert c.thinking_mode is False
    assert c.system_prompt is None


def test_conversation_with_snapshot():
    c = Conversation(
        provider_id="openai-test-abc",
        model_id="gpt-4o",
        temperature=0.3,
        max_tokens=2048,
        streaming_enabled=True,
    )
    assert c.provider_id == "openai-test-abc"
    assert c.model_id == "gpt-4o"
    assert c.temperature == 0.3
    assert c.max_tokens == 2048


def test_conversation_timestamps():
    c = Conversation()
    assert c.created_at is not None
    assert c.updated_at is not None
    assert c.created_at <= datetime.now(timezone.utc)


def test_conversation_is_branch():
    c = Conversation()
    assert c.is_branch is False
    c.parent_id = "parent-123"
    assert c.is_branch is True


def test_message_defaults():
    m = Message()
    assert m.id != ""
    assert m.role == MessageRole.USER
    assert m.content == ""
    assert m.tokens_used == 0
    assert m.timestamp is not None


def test_message_with_content():
    m = Message(
        conversation_id="conv-1",
        role=MessageRole.ASSISTANT,
        content="Hello!",
        tokens_used=10,
    )
    assert m.conversation_id == "conv-1"
    assert m.role == MessageRole.ASSISTANT
    assert m.content == "Hello!"
    assert m.tokens_used == 10


def test_message_role_from_string():
    m = Message(role="user")
    assert m.role == MessageRole.USER


def test_conversation_title_is_custom():
    c = Conversation()
    assert c.title_is_custom is False
    c.metadata["title_is_custom"] = True
    assert c.title_is_custom is True


def test_conversation_id_unique():
    c1 = Conversation()
    c2 = Conversation()
    assert c1.id != c2.id


# ── Regression: set_provider_model (Defect 1) ────────────────────

import pytest


@pytest.mark.asyncio
async def test_conversation_manager_set_provider_model():
    """ConversationManager.set_provider_model persists provider/model to conversation."""
    from aios.conversation.manager import ConversationManager
    mgr = ConversationManager(ai_router=None)
    conv = await mgr.create_conversation(title="test")
    assert conv.provider_id is None
    assert conv.model_id is None

    updated = await mgr.set_provider_model(conv.id, provider_id="google-4b8ab864", model_id="gemini-2.5-flash")
    assert updated.provider_id == "google-4b8ab864"
    assert updated.model_id == "gemini-2.5-flash"

    fetched = await mgr.get_conversation(conv.id)
    assert fetched.provider_id == "google-4b8ab864"
    assert fetched.model_id == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_conversation_manager_set_provider_model_partial():
    """set_provider_model only updates provided fields."""
    from aios.conversation.manager import ConversationManager
    mgr = ConversationManager(ai_router=None)
    conv = await mgr.create_conversation(title="test", provider_id="old-provider", model_id="old-model")

    updated = await mgr.set_provider_model(conv.id, model_id="new-model")
    assert updated.provider_id == "old-provider"
    assert updated.model_id == "new-model"


@pytest.mark.asyncio
async def test_conversation_service_set_provider_model():
    """ConversationService.set_provider_model delegates to manager."""
    from aios.conversation.manager import ConversationManager
    from aios.conversation.service import ConversationService
    mgr = ConversationManager(ai_router=None)
    svc = ConversationService(mgr)

    conv = await svc.create_conversation(title="test")
    updated = await svc.set_provider_model(conv.id, provider_id="groq-xyz", model_id="llama-3.1-8b")
    assert updated.provider_id == "groq-xyz"
    assert updated.model_id == "llama-3.1-8b"


@pytest.mark.asyncio
async def test_conversation_service_create_with_provider_model():
    """ConversationService.create_conversation accepts provider_id/model_id."""
    from aios.conversation.manager import ConversationManager
    from aios.conversation.service import ConversationService
    mgr = ConversationManager(ai_router=None)
    svc = ConversationService(mgr)

    conv = await svc.create_conversation(title="test", provider_id="openai-abc", model_id="gpt-4o")
    assert conv.provider_id == "openai-abc"
    assert conv.model_id == "gpt-4o"

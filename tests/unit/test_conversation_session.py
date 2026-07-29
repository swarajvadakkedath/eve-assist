"""Tests for SessionManager."""

import pytest
from datetime import datetime, timedelta
from aios.conversation.session import SessionManager
from aios.conversation.exceptions import SessionNotFoundError


@pytest.mark.asyncio
class TestSessionManager:
    async def test_create_session(self):
        sm = SessionManager()
        session = await sm.create_session("conv-1")
        assert session.session_id
        assert session.conversation_id == "conv-1"
        assert session.created_at is not None
        assert session.expires_at is not None

    async def test_create_session_with_context(self):
        sm = SessionManager()
        session = await sm.create_session("conv-1", context={"app": "vscode"})
        assert session.current_context["app"] == "vscode"

    async def test_get_session(self):
        sm = SessionManager()
        created = await sm.create_session("conv-1")
        fetched = await sm.get_session(created.session_id)
        assert fetched is not None
        assert fetched.session_id == created.session_id

    async def test_get_session_not_found(self):
        sm = SessionManager()
        result = await sm.get_session("nonexistent")
        assert result is None

    async def test_get_or_create_session_existing(self):
        sm = SessionManager()
        created = await sm.create_session("conv-1")
        fetched = await sm.get_or_create_session("conv-1")
        assert fetched.session_id == created.session_id

    async def test_get_or_create_session_new(self):
        sm = SessionManager()
        session = await sm.get_or_create_session("conv-new")
        assert session.conversation_id == "conv-new"

    async def test_get_or_create_session_refreshes_expiry(self):
        sm = SessionManager(session_timeout_minutes=60)
        created = await sm.create_session("conv-1")
        old_expiry = created.expires_at
        await sm.get_or_create_session("conv-1")
        assert created.expires_at > old_expiry

    async def test_update_session_context(self):
        sm = SessionManager()
        session = await sm.create_session("conv-1")
        updated = await sm.update_session_context(session.session_id, {"file": "/tmp/test.txt"})
        assert updated.current_context["file"] == "/tmp/test.txt"

    async def test_update_session_context_merges(self):
        sm = SessionManager()
        session = await sm.create_session("conv-1", context={"app": "vscode"})
        updated = await sm.update_session_context(session.session_id, {"file": "/tmp/test.txt"})
        assert updated.current_context["app"] == "vscode"
        assert updated.current_context["file"] == "/tmp/test.txt"

    async def test_update_session_context_not_found(self):
        sm = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await sm.update_session_context("nonexistent", {"key": "val"})

    async def test_delete_session(self):
        sm = SessionManager()
        session = await sm.create_session("conv-1")
        await sm.delete_session(session.session_id)
        result = await sm.get_session(session.session_id)
        assert result is None

    async def test_list_sessions(self):
        sm = SessionManager()
        await sm.create_session("conv-1")
        await sm.create_session("conv-2")
        sessions = await sm.list_sessions()
        assert len(sessions) == 2

    async def test_list_sessions_by_conversation(self):
        sm = SessionManager()
        s1 = await sm.create_session("conv-1")
        s2 = await sm.create_session("conv-1")
        s3 = await sm.create_session("conv-2")
        conv1_sessions = await sm.list_sessions("conv-1")
        assert len(conv1_sessions) == 2
        conv2_sessions = await sm.list_sessions("conv-2")
        assert len(conv2_sessions) == 1

    async def test_list_sessions_empty(self):
        sm = SessionManager()
        sessions = await sm.list_sessions()
        assert sessions == []

    async def test_cleanup_expired(self):
        sm = SessionManager(session_timeout_minutes=-1)
        await sm.create_session("conv-expired")
        cleaned = await sm.cleanup_expired()
        assert cleaned >= 1

    async def test_cleanup_expired_no_expired(self):
        sm = SessionManager(session_timeout_minutes=60)
        await sm.create_session("conv-1")
        cleaned = await sm.cleanup_expired()
        assert cleaned == 0

    async def test_get_session_returns_none_for_expired(self):
        sm = SessionManager(session_timeout_minutes=-1)
        session = await sm.create_session("conv-expired")
        result = await sm.get_session(session.session_id)
        assert result is None

    async def test_custom_timeout(self):
        sm = SessionManager(session_timeout_minutes=5)
        session = await sm.create_session("conv-1")
        expected_expiry = session.created_at + timedelta(minutes=5)
        assert abs((session.expires_at - expected_expiry).total_seconds()) < 1

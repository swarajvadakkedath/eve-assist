"""Pytest fixtures for AIOS tests."""

import pytest
from aios.core.event_bus import EventBus
from aios.core.di_container import DIContainer
from aios.core.permission_manager import PermissionManager
from aios.core.tool_manager import ToolManager
from aios.core.ai_router import AIRouter
from aios.core.memory_system import MemorySystem
from aios.core.planner import Planner
from aios.core.context_engine import ContextEngine
from aios.core.conversation import ConversationSystem
from aios.core.capability_registry import CapabilityRegistry


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def permissions():
    return PermissionManager()


@pytest.fixture
def tool_manager(permissions):
    return ToolManager(permissions)


@pytest.fixture
def memory():
    return MemorySystem()


@pytest.fixture
def planner():
    return Planner()


@pytest.fixture
def context():
    return ContextEngine()


@pytest.fixture
def conversation():
    return ConversationSystem()


@pytest.fixture
def capability_registry():
    return CapabilityRegistry()


@pytest.fixture
def di_container():
    return DIContainer()

"""FastAPI application factory with full module wiring."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aios.config.settings import AiosSettings
from aios.utils.logger import setup_logging, get_logger
from aios.core.event_bus import EventBus
from aios.core.di_container import DIContainer
from aios.core.ai_router import AIRouter
from aios.core.permission_manager import PermissionManager
from aios.core.tool_manager import ToolManager
from aios.core.capability_registry import CapabilityRegistry
from aios.core.memory_system import MemorySystem
from aios.core.planner import Planner
from aios.core.context_engine import ContextEngine
from aios.conversation.manager import ConversationManager
from aios.conversation.service import ConversationService
from aios.tools.builtin import register_builtin_tools
from aios.tools.system_tools import register_system_tools
from aios.execution.engine import ExecutionEngine
from aios.workspace.manager import WorkspaceManager
from aios.workspace.service import WorkspaceService
from aios.desktop.status_service import StatusService, AppStatus
from aios.desktop.settings_store import SettingsStore
from aios.desktop.app_shell import AppShell
from aios.desktop.hotkeys import HotkeyManager
from aios.desktop.notifications import NotificationService
from aios.desktop.window_manager import WindowManager
from aios.desktop.startup import StartupManager
from aios.plugins.plugin_manager import PluginManager

logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global logger
    settings = AiosSettings()
    setup_logging(settings.log_level, settings.log_format)
    logger = get_logger(__name__)

    di = DIContainer()

    event_bus = EventBus(
        max_retries=settings.event_bus_max_retries,
        retry_delay=settings.event_bus_retry_delay,
    )
    await event_bus.start()

    permissions = PermissionManager()
    tool_manager = ToolManager(permissions)
    capability_registry = CapabilityRegistry()
    ai_router = AIRouter()
    memory = MemorySystem()
    planner = Planner()
    context = ContextEngine(poll_interval=settings.context_poll_interval)

    conversation_manager = ConversationManager(
        ai_router=ai_router,
        memory_system=memory,
        planner=planner,
        tool_manager=tool_manager,
        capability_registry=capability_registry,
        context_engine=context,
    )
    conversation_service = ConversationService(
        manager=conversation_manager,
        event_bus=event_bus,
    )

    register_builtin_tools(tool_manager)
    register_system_tools(tool_manager, event_bus)

    status_service = StatusService()
    settings_store = SettingsStore()
    await settings_store.initialize()
    app_shell = AppShell()
    hotkey_manager = HotkeyManager()
    await hotkey_manager.initialize(settings_store)
    notification_service = NotificationService()
    await notification_service.initialize(settings_store)
    window_manager = WindowManager()
    await window_manager.initialize(settings_store)
    startup_manager = StartupManager()
    await startup_manager.initialize(settings_store)

    execution_engine = ExecutionEngine(
        planner=planner,
        capability_registry=capability_registry,
        tool_manager=tool_manager,
        permission_manager=permissions,
        event_bus=event_bus,
    )

    workspace_manager = WorkspaceManager(event_bus=event_bus, memory=memory)
    workspace_service = WorkspaceService(workspace_manager)
    await workspace_manager.start()

    # Plugin system — wired with all core services
    plugin_manager = PluginManager(
        tool_manager=tool_manager,
        capability_registry=capability_registry,
        event_bus=event_bus,
        permission_manager=permissions,
    )
    await plugin_manager.initialize()

    async def on_status_change(status: AppStatus, metadata: dict):
        await event_bus.publish("desktop:status", {"status": status.value, "metadata": metadata})
    status_service = StatusService()
    status_service.subscribe(on_status_change)

    di.register(StatusService, lambda: status_service)
    di.register(SettingsStore, lambda: SettingsStore())
    di.register(AppShell, lambda: AppShell())
    di.register(HotkeyManager, lambda: HotkeyManager())
    di.register(NotificationService, lambda: NotificationService())
    di.register(WindowManager, lambda: WindowManager())
    di.register(StartupManager, lambda: StartupManager())
    di.register(ExecutionEngine, lambda: execution_engine)
    di.register(WorkspaceManager, lambda: workspace_manager)
    di.register(WorkspaceService, lambda: workspace_service)
    di.register(PermissionManager, lambda: permissions)
    di.register(ToolManager, lambda: tool_manager)
    di.register(CapabilityRegistry, lambda: capability_registry)
    di.register(AIRouter, lambda: ai_router)
    di.register(MemorySystem, lambda: memory)
    di.register(Planner, lambda: planner)
    di.register(ContextEngine, lambda: context)
    di.register(ConversationManager, lambda: conversation_manager)
    di.register(ConversationService, lambda: conversation_service)

    app.state.di = di
    app.state.event_bus = event_bus
    app.state.tool_manager = tool_manager
    app.state.capability_registry = capability_registry
    app.state.ai_router = ai_router
    app.state.memory = memory
    app.state.planner = planner
    app.state.context = context
    app.state.conversation_service = conversation_service
    app.state.permissions = permissions
    app.state.workspace_manager = workspace_manager
    app.state.workspace_service = workspace_service
    app.state.plugin_manager = plugin_manager
    app.state.execution_engine = execution_engine

    logger.info("aios.started", version="1.0.0")
    await event_bus.publish("system:startup", {"version": "1.0.0"})

    yield

    await workspace_manager.stop()
    await plugin_manager.shutdown()
    await event_bus.publish("system:shutdown", {"reason": "app_stop"})
    await event_bus.stop()
    logger.info("aios.stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS API",
        version="1.0.0",
        description="AI Operating System - Intelligent layer for Windows",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routes(app)

    return app


def register_routes(app: FastAPI):
    from aios.api.chat import router as chat_router
    from aios.api.tools import router as tools_router
    from aios.api.capabilities import router as capabilities_router
    from aios.api.settings import router as settings_router
    from aios.api.plugins import router as plugins_router

    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(tools_router, prefix="/api/v1")
    app.include_router(capabilities_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    app.include_router(plugins_router, prefix="/api/v1")

    from aios.api.desktop import router as desktop_router
    app.include_router(desktop_router)

    from aios.api.execution import router as execution_router
    app.include_router(execution_router)

    from aios.api.workspace import router as workspace_router
    app.include_router(workspace_router, prefix="/api/v1")

    @app.get("/api/v1/system/health")
    async def health_check(request):
        eb = request.app.state.event_bus
        return {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 0,
            "modules": {
                "event_bus": "healthy",
                "ai_router": "healthy",
                "tool_manager": "healthy",
                "memory_system": "healthy",
            },
        }

    @app.get("/api/v1/system/status")
    async def system_status(request):
        return {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "active_providers": [],
            "active_tools": 0,
            "active_conversations": 0,
            "uptime": 0,
        }

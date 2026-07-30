"""FastAPI application factory with full module wiring."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from aios.core.auth import AuthManager

from aios.config.settings import AiosSettings
from aios.utils.logger import setup_logging, get_logger
from aios.utils.tracer import trace_async
from aios.core.event_bus import EventBus
from aios.core.smart_router import SmartRouter
from aios.core.permission_manager import PermissionManager
from aios.core.provider_manager import ProviderManager
from aios.core.tool_manager import ToolManager
from aios.core.capability_registry import CapabilityRegistry
from aios.core.memory_system import MemorySystem
from aios.core.planner import Planner
from aios.core.context_engine import ContextEngine
from aios.conversation.manager import ConversationManager
from aios.conversation.service import ConversationService
from aios.conversation.file_repository import FileConversationRepository
from aios.tools.builtin import register_builtin_tools
from aios.tools.system_tools import register_system_tools
from aios.tools.content_tools import register_content_tools
from aios.tools.developer_tools import register_developer_tools
from aios.tools.devtools_tools import register_devtools_tools
from aios.tools.git_tools import register_git_tools
from aios.tools.network_tools import register_network_tools
from aios.tools.office_tools import register_office_tools
from aios.tools.productivity_tools import register_productivity_tools
from aios.tools.browser_tools import register_browser_tools
from aios.devtools.debug_console import DebugConsole
from aios.devtools.health_dashboard import HealthDashboard
from aios.devtools.module_inspector import ModuleInspector
from aios.devtools.hot_reload import HotReload
from aios.devtools.diagnostics import Diagnostics
from aios.devtools.performance_monitor import PerformanceMonitor
from aios.devtools.log_viewer import LogViewer
from aios.browser.engine import BrowserEngine
from aios.execution.engine import ExecutionEngine
from aios.workspace.manager import WorkspaceManager
from aios.workspace.service import WorkspaceService
from aios.desktop.status_service import StatusService, AppStatus
from aios.desktop.settings_store import SettingsStore
from aios.desktop.hotkeys import HotkeyManager
from aios.desktop.notifications import NotificationService
from aios.desktop.window_manager import WindowManager
from aios.desktop.startup import StartupManager
from aios.plugins.plugin_manager import PluginManager
from aios.voice.stt import STTEngine
from aios.voice.tts import TTSEngine
from aios.voice.session import VoiceSession
from aios.voice.pipeline import VoicePipeline
from aios.voice.events import VoiceEventPublisher
from aios.voice.models import VoiceConfig, STTProvider, TTSProvider
from aios.vision.engine import VisionEngine
from aios.vision.session import VisionSession
from aios.vision.pipeline import VisionPipeline
from aios.vision.events import VisionEventPublisher
from aios.vision.models import VisionConfig, VisionProvider, OCREngine

logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global logger
    settings = AiosSettings()
    setup_logging(settings.log_level, settings.log_format)
    logger = get_logger(__name__)
    logger.info("lifespan.startup_beginning")

    auth_manager = AuthManager()
    app.state.auth_manager = auth_manager
    logger.info("auth.token_generated", token_prefix=auth_manager.token[:8] + "...")

    event_bus = EventBus(
        max_retries=settings.event_bus_max_retries,
        retry_delay=settings.event_bus_retry_delay,
    )
    await event_bus.start()

    permissions = PermissionManager(event_bus=event_bus, config=settings)
    permissions.configure(
        default_level=settings.permission_default_level,
        sensitive_actions=list(settings.permission_sensitive_actions),
        session_timeout=float(settings.session_timeout_seconds),
    )
    capability_registry = CapabilityRegistry()
    tool_manager = ToolManager(permissions, capability_registry, event_bus)
    smart_router = SmartRouter()
    provider_manager = ProviderManager(smart_router=smart_router)
    provider_manager.register_all_adapters()
    memory = MemorySystem(event_bus=event_bus)
    planner = Planner()
    from aios.core.windows.adapter import WindowsAdapter
    windows_adapter = WindowsAdapter(
        permission_manager=permissions,
        event_bus=event_bus,
    )
    context = ContextEngine(
        windows_adapter=windows_adapter,
        event_bus=event_bus,
        poll_interval=settings.context_poll_interval,
        memory_store=memory,
    )

    conversation_repo = FileConversationRepository()
    conversation_repo.recover()

    conversation_manager = ConversationManager(
        ai_router=smart_router,
        memory_system=memory,
        planner=planner,
        tool_manager=tool_manager,
        capability_registry=capability_registry,
        context_engine=context,
        repository=conversation_repo,
    )
    conversation_service = ConversationService(
        manager=conversation_manager,
        event_bus=event_bus,
    )

    register_builtin_tools(tool_manager)
    register_system_tools(tool_manager, event_bus)

    settings_store = SettingsStore()
    await settings_store.initialize()
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

    voice_config = VoiceConfig(
        stt_provider=STTProvider(settings.voice_stt_engine or "whisper"),
        tts_provider=TTSProvider(settings.voice_tts_engine or "pyttsx3"),
        language=settings.ui_language or "en-US",
        wake_word=settings.voice_wake_word or "hey eve",
    )
    stt_engine = STTEngine(provider=voice_config.stt_provider)
    tts_engine = TTSEngine(provider=voice_config.tts_provider)
    voice_event_publisher = VoiceEventPublisher(event_bus)
    voice_session = VoiceSession(
        stt_engine=stt_engine,
        tts_engine=tts_engine,
        conversation_service=conversation_service,
        event_publisher=voice_event_publisher,
        config=voice_config,
    )
    voice_pipeline = VoicePipeline(
        session=voice_session,
        stt_engine=stt_engine,
        tts_engine=tts_engine,
        conversation_service=conversation_service,
        event_publisher=voice_event_publisher,
    )

    vision_config = VisionConfig(
        provider=VisionProvider(settings.vision_provider or "builtin"),
        ocr_engine=OCREngine(settings.vision_ocr_engine or "tesseract"),
        capture_quality=getattr(settings, "vision_capture_quality", 75),
    )
    vision_engine = VisionEngine(config=vision_config)
    vision_event_publisher = VisionEventPublisher(event_bus)
    vision_session = VisionSession(engine=vision_engine, config=vision_config)
    vision_pipeline = VisionPipeline(
        vision_session=vision_session,
        conversation_manager=conversation_manager,
        event_publisher=vision_event_publisher,
        config=vision_config,
    )
    from aios.vision.tools import register_vision_tools
    register_vision_tools(tool_manager, vision_engine, vision_session)

    browser_engine = BrowserEngine(vision_engine=vision_engine, event_bus=event_bus)
    register_browser_tools(tool_manager, browser_engine, vision_engine, event_bus)

    register_content_tools(tool_manager, event_bus)
    register_developer_tools(tool_manager, event_bus)
    register_git_tools(tool_manager, event_bus)
    register_network_tools(tool_manager, event_bus)
    register_office_tools(tool_manager, event_bus)
    register_productivity_tools(tool_manager, event_bus)

    debug_console = DebugConsole()
    health_dashboard = HealthDashboard(memory=memory, event_bus=event_bus)
    module_inspector = ModuleInspector()
    hot_reload = HotReload(event_bus=event_bus)
    diagnostics = Diagnostics(windows_adapter=windows_adapter, memory=memory, event_bus=event_bus)
    performance_monitor = PerformanceMonitor(event_bus=event_bus)
    log_viewer = LogViewer(event_bus=event_bus)
    register_devtools_tools(
        tool_manager,
        debug_console=debug_console,
        health_dashboard=health_dashboard,
        module_inspector=module_inspector,
        hot_reload=hot_reload,
        diagnostics=diagnostics,
        performance_monitor=performance_monitor,
        log_viewer=log_viewer,
        event_bus=event_bus,
    )

    app.state.browser_engine = browser_engine
    app.state.event_bus = event_bus
    app.state.tool_manager = tool_manager
    app.state.capability_registry = capability_registry
    app.state.smart_router = smart_router
    app.state.provider_manager = provider_manager
    app.state.memory = memory
    app.state.planner = planner
    app.state.context = context
    app.state.conversation_service = conversation_service
    app.state.permissions = permissions
    app.state.workspace_manager = workspace_manager
    app.state.workspace_service = workspace_service
    app.state.plugin_manager = plugin_manager
    app.state.execution_engine = execution_engine
    app.state.voice_session = voice_session
    app.state.voice_pipeline = voice_pipeline
    app.state.stt_engine = stt_engine
    app.state.tts_engine = tts_engine
    app.state.voice_event_publisher = voice_event_publisher
    app.state.vision_engine = vision_engine
    app.state.vision_session = vision_session
    app.state.vision_pipeline = vision_pipeline
    app.state.vision_event_publisher = vision_event_publisher
    import aios.api.vision as vision_api
    vision_api.vision_session = vision_session

    app.state.debug_console = debug_console
    app.state.health_dashboard = health_dashboard
    app.state.module_inspector = module_inspector
    app.state.hot_reload = hot_reload
    app.state.diagnostics = diagnostics
    app.state.performance_monitor = performance_monitor
    app.state.log_viewer = log_viewer
    app.state.windows_adapter = windows_adapter

    logger.info("aios.started", version="1.1.0-rc.2")
    await event_bus.publish("system:startup", {"version": "1.1.0-rc.2"})

    await status_service.set_status(AppStatus.READY)

    yield

    await hot_reload.stop()
    await performance_monitor.stop()
    await voice_session.cleanup()
    await stt_engine.cleanup()
    await tts_engine.cleanup()
    await vision_session.stop()
    await browser_engine.shutdown()
    await workspace_manager.stop()
    await plugin_manager.shutdown()
    await provider_manager.shutdown()
    await event_bus.publish("system:shutdown", {"reason": "app_stop"})
    await event_bus.stop()
    logger.info("aios.stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIOS API",
        version="1.1.0-rc.2",
        description="AI Operating System - Intelligent layer for Windows",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost", "https://tauri.localhost"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routes(app)

    return app


def register_routes(app: FastAPI):
    from aios.api.permissions import router as permissions_router

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
    app.include_router(permissions_router, prefix="/api/v1")

    from aios.api.memory import router as memory_router
    app.include_router(memory_router, prefix="/api/v1")

    from aios.api.desktop import router as desktop_router
    app.include_router(desktop_router)

    from aios.api.execution import router as execution_router
    app.include_router(execution_router)

    from aios.api.workspace import router as workspace_router
    app.include_router(workspace_router, prefix="/api/v1")

    from aios.api.voice import router as voice_router
    app.include_router(voice_router)

    from aios.api.vision import router as vision_router
    app.include_router(vision_router)

    from aios.api.providers import router as providers_router
    app.include_router(providers_router)

    @app.get("/api/v1/system/health")
    async def health_check(request: Request):
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
    async def system_status(request: Request):
        return {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "active_providers": [],
            "active_tools": 0,
            "active_conversations": 0,
            "uptime": 0,
        }

    @app.get("/api/v1/auth/token")
    async def get_auth_token(request: Request):
        client_host = request.client.host if request.client else ""
        if client_host not in ("127.0.0.1", "::1", "localhost"):
            raise HTTPException(status_code=403)
        auth_manager: AuthManager = request.app.state.auth_manager
        return {"token": auth_manager.token}

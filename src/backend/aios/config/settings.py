"""Centralized configuration using Pydantic settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AiosSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
    )

    # AI Provider
    ai_provider: str = "ollama"
    ai_api_key: str = ""
    ai_model: str = "gpt-4"
    ai_embedding_model: str = "text-embedding-3-small"
    ai_max_tokens: int = 4096
    ai_temperature: float = 0.7
    ai_timeout: int = 60

    # Database
    db_path: str = str(Path.home() / ".aios" / "aios.db")

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    # Permissions
    permission_default_level: int = 1
    session_timeout_seconds: int = 300
    permission_sensitive_actions: list[str] = []

    # Event Bus
    event_bus_max_retries: int = 3
    event_bus_retry_delay: float = 1.0
    event_bus_history_limit: int = 1000

    # UI
    ui_theme: Literal["light", "dark", "system"] = "system"
    ui_language: str = "en"

    # Plugins
    plugins_enabled: bool = True
    plugins_path: str = str(Path.home() / ".aios" / "plugins")

    # Windows Adapter
    windows_adapter_timeout: int = 30

    # Vision
    vision_provider: str = "builtin"
    vision_ocr_engine: str = "tesseract"
    vision_capture_quality: int = 75
    vision_tesseract_path: str = "tesseract"

    # Memory
    memory_importance_threshold: float = 0.3
    memory_prune_days: int = 90

    # Context Engine
    context_poll_interval: float = 2.0

    # Provider health + model refresh intervals (seconds; None disables the loop)
    provider_health_interval: float | None = 120.0
    model_refresh_interval: float | None = 3600.0

    # Planner
    planner_step_timeout: int = 30
    planner_max_steps: int = 20

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_tokens_per_minute: int = 100000

    # Voice
    voice_stt_engine: str = "whisper"
    voice_tts_engine: str = "pyttsx3"
    voice_wake_word: str = "hey eve"

    # Network
    api_host: str = "127.0.0.1"
    api_port: int = 8456

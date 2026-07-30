"""Default configuration values for AIOS."""

from pathlib import Path

DEFAULT_CONFIG = {
    "ai": {
        "provider": "ollama",
        "model": "gpt-4",
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout": 60,
    },
    "database": {
        "path": str(Path.home() / ".aios" / "aios.db"),
    },
    "logging": {
        "level": "INFO",
        "format": "console",
    },
    "permissions": {
        "default_level": 1,
        "session_timeout": 300,
    },
    "event_bus": {
        "max_retries": 3,
        "retry_delay": 1.0,
        "history_limit": 1000,
    },
    "ui": {
        "theme": "system",
        "language": "en",
    },
    "plugins": {
        "enabled": True,
        "path": str(Path.home() / ".aios" / "plugins"),
    },
    "windows_adapter": {
        "timeout": 30,
    },
    "vision": {
        "tesseract_path": "tesseract",
    },
    "memory": {
        "importance_threshold": 0.3,
        "prune_days": 90,
    },
    "context_engine": {
        "poll_interval": 2.0,
    },
    "planner": {
        "step_timeout": 30,
        "max_steps": 20,
    },
    "rate_limiting": {
        "requests_per_minute": 60,
        "tokens_per_minute": 100000,
    },
    "voice": {
        "stt_engine": "whisper",
        "tts_engine": "edge",
        "wake_word": "hey eve",
    },
    "network": {
        "host": "127.0.0.1",
        "port": 8456,
    },
    "providers": {
        "openai": {
            "model": "gpt-4",
            "embedding_model": "text-embedding-3-small",
        },
        "anthropic": {
            "model": "claude-3-sonnet-20240229",
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "llama3.2",
        },
    },
}

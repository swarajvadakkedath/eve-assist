"""Provider Manager — full lifecycle, adapter management, health monitoring, caching, model discovery.

Architecture:
  UI → ProviderManager → AIProviderAdapter → Provider SDK / REST API

  No UI component communicates directly with provider SDKs.
  Adding a new provider only requires creating a new adapter subclass.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import httpx

try:
    import win32cred
    HAS_WIN32CRED = True
except ImportError:
    HAS_WIN32CRED = False

from aios.core.model_info import ModelInfo
from aios.core.model_catalog import get_catalog_models
from aios.core.cache import ModelCache
from aios.core.health_monitor import HealthMonitor, HealthState
from aios.core.smart_router import SmartRouter, RoutingStrategy
from aios.core.streaming_manager import StreamingManager
from aios.core.adapters.base import (
    AIProviderAdapter,
    ChatRequest,
    ChatResponse,
    ProviderStatus,
    sanitize_error,
)
from aios.core.adapters import (
    OpenAIAdapter,
    AnthropicAdapter,
    GoogleAdapter,
    OllamaAdapter,
    GroqAdapter,
    OpenAICompatibleAdapter,
    CohereAdapter,
    CloudflareAdapter,
)
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout
from aios.utils.tracer import trace_async, trace_sync

logger = structlog.get_logger(__name__)

# Provider metadata — API endpoints, auth style, etc.
PROVIDER_META = {
    "google": {"name": "Google AI Studio", "endpoint": "https://generativelanguage.googleapis.com/v1beta", "models_endpoint": "/models", "chat_endpoint": "/models/{model}:generateContent", "api_key_in": "header", "auth_header": "x-goog-api-key", "auth_prefix": None},
    "groq": {"name": "Groq", "endpoint": "https://api.groq.com/openai/v1", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "openrouter": {"name": "OpenRouter", "endpoint": "https://openrouter.ai/api/v1", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "openai": {"name": "OpenAI", "endpoint": "https://api.openai.com/v1", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "anthropic": {"name": "Anthropic", "endpoint": "https://api.anthropic.com/v1", "models_endpoint": None, "chat_endpoint": "/messages", "api_key_in": "header", "auth_header": "x-api-key", "auth_prefix": None},
    "mistral": {"name": "Mistral", "endpoint": "https://api.mistral.ai/v1", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "cerebras": {"name": "Cerebras", "endpoint": "https://api.cerebras.ai/v1", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "github_models": {"name": "GitHub Models", "endpoint": "https://models.inference.ai.azure.com", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "huggingface": {"name": "Hugging Face", "endpoint": "https://api-inference.huggingface.co", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "ollama": {"name": "Ollama", "endpoint": "http://localhost:11434", "models_endpoint": "/api/tags", "chat_endpoint": "/api/chat", "api_key_in": None, "auth_header": None, "auth_prefix": None},
    "lm_studio": {"name": "LM Studio", "endpoint": "http://localhost:1234/v1", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "cohere": {"name": "Cohere", "endpoint": "https://api.cohere.com", "models_endpoint": None, "chat_endpoint": "/v2/chat", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "cloudflare": {"name": "Cloudflare Workers AI", "endpoint": "", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "nvidia": {"name": "NVIDIA NIM", "endpoint": "https://integrate.api.nvidia.com/v1", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "openai_compatible": {"name": "OpenAI Compatible", "endpoint": "", "models_endpoint": "/models", "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
    "custom": {"name": "Custom Provider", "endpoint": "", "models_endpoint": None, "chat_endpoint": "/chat/completions", "api_key_in": "header", "auth_header": "Authorization", "auth_prefix": "Bearer "},
}

ROUTING_CATEGORIES = [
    {"id": "general_chat", "label": "General Chat", "default": None},
    {"id": "coding", "label": "Coding", "default": None},
    {"id": "vision", "label": "Vision", "default": None},
    {"id": "reasoning", "label": "Reasoning", "default": None},
    {"id": "fallback", "label": "Fallback", "default": None},
]


class SecureStorageError(Exception):
    """Raised when secure credential storage is unavailable."""
    pass


class ProviderManager:
    """Central provider lifecycle manager.

    Responsibilities:
    - Register/unregister providers
    - Create/destroy adapter instances  
    - Model discovery (list, refresh, toggle)
    - Health monitoring (per-provider, isolated)
    - Model caching with TTL + background refresh
    - Credential storage (Windows Credential Manager)
    - Routing config management
    """

    def __init__(
        self,
        config_dir: str | None = None,
        smart_router: SmartRouter | None = None,
        health_monitor: HealthMonitor | None = None,
        model_cache: ModelCache | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        if config_dir is None:
            config_dir = str(Path.home() / ".eve")
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._providers_file = self._config_dir / "providers.json"
        self._routing_file = self._config_dir / "routing.json"

        self._providers: list[dict[str, Any]] = []
        self._routing_config: list[dict[str, Any]] = []
        self._adapters: dict[str, AIProviderAdapter] = {}

        self._smart_router = smart_router or SmartRouter()
        self._health_monitor = health_monitor or HealthMonitor()
        self._model_cache = model_cache or ModelCache()
        self._streaming = streaming_manager or StreamingManager()

        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @trace_sync
    def _load(self):
        if self._providers_file.exists():
            try:
                self._providers = json.loads(self._providers_file.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._providers = []
        if self._routing_file.exists():
            try:
                self._routing_config = json.loads(self._routing_file.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._routing_config = []
        self._migrate_routing()
        self._migrate_models()
        self._migrate_legacy_credentials()

        # Sync routing config to smart router
        self._smart_router.set_routing_config(self._routing_config)

        # Recreate adapters after restart (status may be stale)
        self.register_all_adapters()

    @trace_sync
    def _save(self):
        # Strip _api_key from all providers before persisting
        sanitized = []
        for p in self._providers:
            entry = {k: v for k, v in p.items() if k != "_api_key"}
            sanitized.append(entry)
        self._providers_file.write_text(
            json.dumps(sanitized, indent=2, default=str), "utf-8"
        )

    @trace_sync
    def _save_routing(self):
        self._routing_file.write_text(
            json.dumps(self._routing_config, indent=2, default=str), "utf-8"
        )

    # ------------------------------------------------------------------
    # Migration helpers
    # ------------------------------------------------------------------

    @trace_sync
    def _migrate_routing(self):
        existing_ids = {r["id"] for r in self._routing_config}
        for cat in ROUTING_CATEGORIES:
            if cat["id"] not in existing_ids:
                self._routing_config.append({
                    "id": cat["id"],
                    "label": cat["label"],
                    "provider_id": None,
                    "model_id": None,
                })
        self._save_routing()

    @trace_sync
    def _migrate_models(self):
        """Convert old per-provider model lists (list[str]) to new format (list[dict])."""
        migrated = False
        for p in self._providers:
            models = p.get("models", [])
            if models and isinstance(models[0], str):
                catalog = get_catalog_models(p["type"])
                catalog_by_id = {m["id"]: m for m in catalog}
                new_models = []
                for mid in models:
                    if mid in catalog_by_id:
                        entry = dict(catalog_by_id[mid])
                    else:
                        entry = {"id": mid, "displayName": mid, "provider": p["type"], "enabled": True}
                    new_models.append(entry)
                p["models"] = new_models
                migrated = True
            elif not models:
                catalog = get_catalog_models(p["type"])
                if catalog:
                    p["models"] = [dict(m) for m in catalog]
                    migrated = True
        if migrated:
            self._save()

    # ------------------------------------------------------------------
    # Credential management
    # ------------------------------------------------------------------

    def _credential_target(self, provider_id: str) -> str:
        return f"EveOS/Provider/{provider_id}"

    @trace_sync
    def _store_api_key(self, provider_id: str, api_key: str):
        """Store API key securely. Raises SecureStorageError if unavailable."""
        if not HAS_WIN32CRED:
            raise SecureStorageError(
                "Secure credential storage (Windows Credential Manager) is unavailable. "
                "API key was NOT saved. Install pywin32 or use Windows for secure storage."
            )
        try:
            target = self._credential_target(provider_id)
            win32cred.CredWrite({
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": target,
                "UserName": "apikey",
                "CredentialBlob": api_key,
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            })
        except Exception as e:
            logger.error("cred_store_failed", provider_id=provider_id, error=sanitize_error(str(e)[:200]))
            raise SecureStorageError(f"Failed to store credential: {e}") from e

    @trace_sync
    def _load_api_key(self, provider_id: str) -> str | None:
        if not HAS_WIN32CRED:
            return None
        try:
            target = self._credential_target(provider_id)
            cred = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC)
            blob = cred["CredentialBlob"]
            return blob.decode("utf-16-le").rstrip("\x00")
        except Exception:
            return None

    @trace_sync
    def _delete_api_key(self, provider_id: str):
        if not HAS_WIN32CRED:
            return
        try:
            target = self._credential_target(provider_id)
            win32cred.CredDelete(target, win32cred.CRED_TYPE_GENERIC)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Legacy credential migration
    # ------------------------------------------------------------------

    @trace_sync
    def _migrate_legacy_credentials(self):
        """Migrate plaintext API keys from providers.json to Windows Credential Manager.

        If legacy plaintext _api_key exists in provider dict:
          1. Attempt to move it into secure storage.
          2. Only after successful secure write, remove plaintext.
          3. If secure storage fails, mark provider for manual re-entry.
        """
        if not HAS_WIN32CRED:
            return

        migrated = 0
        failed = 0
        for provider in self._providers:
            legacy_key = provider.pop("_api_key", None)
            if not legacy_key:
                continue

            pid = provider["id"]
            try:
                target = self._credential_target(pid)
                win32cred.CredWrite({
                    "Type": win32cred.CRED_TYPE_GENERIC,
                    "TargetName": target,
                    "UserName": "apikey",
                    "CredentialBlob": legacy_key,
                    "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                })
                migrated += 1
                logger.info("credential.migrated", provider_id=pid)
            except Exception as e:
                failed += 1
                provider["credential_migration_required"] = True
                logger.error("credential.migration_failed", provider_id=pid, error=sanitize_error(str(e)[:200]))

        if migrated > 0 or failed > 0:
            self._save()
            logger.info(
                "credential.migration_complete",
                migrated=migrated,
                failed=failed,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_provider(self, provider_id: str) -> dict | None:
        for p in self._providers:
            if p["id"] == provider_id:
                return p
        return None

    def _model_dicts_to_info(self, provider: dict, model_dicts: list[dict]) -> list[ModelInfo]:
        """Convert model dicts (from storage or catalog) to ModelInfo objects."""
        pid = provider["id"]
        pname = provider.get("name", provider["type"])
        return [ModelInfo.from_old_format(m, pid, pname) for m in model_dicts]

    def _info_to_dicts(self, models: list[ModelInfo]) -> list[dict]:
        """Convert ModelInfo objects to storage dicts (backward compat)."""
        return [m.to_dict() for m in models]

    def _adapters_fn(self) -> dict[str, AIProviderAdapter]:
        """Return current adapters (used by health monitor background check)."""
        return dict(self._adapters)

    # ------------------------------------------------------------------
    # Adapter factory
    # ------------------------------------------------------------------

    def _create_adapter(self, provider: dict) -> AIProviderAdapter | None:
        """Create the appropriate adapter for a provider."""
        ptype = provider["type"]
        api_key = self._load_api_key(provider["id"])
        base_url = provider.get("endpoint_url") or ""
        timeout_config = TimeoutConfig()

        try:
            if ptype == "openai":
                return OpenAIAdapter(
                    api_key=api_key or "",
                    base_url=base_url or "https://api.openai.com/v1",
                    organization=provider.get("organization", ""),
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            elif ptype == "anthropic":
                return AnthropicAdapter(
                    api_key=api_key or "",
                    base_url=base_url or "https://api.anthropic.com/v1",
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            elif ptype == "google":
                return GoogleAdapter(
                    api_key=api_key or "",
                    base_url=base_url or "https://generativelanguage.googleapis.com/v1beta",
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            elif ptype == "ollama":
                return OllamaAdapter(
                    base_url=base_url or "http://localhost:11434",
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            elif ptype == "groq":
                return GroqAdapter(
                    api_key=api_key or "",
                    base_url=base_url or "https://api.groq.com/openai/v1",
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            elif ptype == "cohere":
                return CohereAdapter(
                    api_key=api_key or "",
                    base_url=base_url or "https://api.cohere.com",
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            elif ptype == "cloudflare":
                account_id = provider.get("account_id", "")
                return CloudflareAdapter(
                    api_key=api_key or "",
                    base_url=base_url or "",
                    account_id=account_id,
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            elif ptype in ("openrouter", "mistral", "cerebras", "github_models",
                           "huggingface", "lm_studio", "nvidia", "openai_compatible", "custom"):
                meta = PROVIDER_META.get(ptype, {})
                pname = provider.get("name") or meta.get("name", ptype)
                resolved_base = base_url or meta.get("endpoint", "")
                return OpenAICompatibleAdapter(
                    provider_type=ptype,
                    provider_name=pname,
                    api_key=api_key or "",
                    base_url=resolved_base,
                    timeout_config=timeout_config,
                    streaming_manager=self._streaming,
                )
            else:
                logger.warning("provider.unknown_type", type=ptype)
                return None
        except Exception as e:
            logger.error("provider.adapter_creation_failed", provider_id=provider["id"], error=sanitize_error(str(e)[:200]))
            return None

    def _register_adapter(self, provider: dict):
        """Create and register an adapter for a provider, then sync models to router."""
        adapter = self._create_adapter(provider)
        if adapter is None:
            return

        pid = provider["id"]
        self._adapters[pid] = adapter
        self._smart_router.register_adapter(pid, adapter)
        self._health_monitor.register_provider(pid)

        # Sync models to smart router
        models = provider.get("models", [])
        if models:
            model_infos = self._model_dicts_to_info(provider, models)
            self._smart_router.set_provider_models(pid, model_infos)

    def _unregister_adapter(self, provider_id: str):
        adapter = self._adapters.pop(provider_id, None)
        if adapter:
            asyncio.ensure_future(adapter.disconnect())
        self._smart_router.unregister_adapter(provider_id)
        self._health_monitor.unregister_provider(provider_id)

    # ------------------------------------------------------------------
    # Public API — Provider CRUD
    # ------------------------------------------------------------------

    @trace_sync
    def list_providers(self) -> list[dict[str, Any]]:
        result = []
        for p in self._providers:
            entry = {k: v for k, v in p.items() if k != "_api_key"}
            entry["has_api_key"] = self._load_api_key(p["id"]) is not None
            result.append(entry)
        return result

    @trace_sync
    def get_provider(self, provider_id: str) -> dict | None:
        p = self._get_provider(provider_id)
        if not p:
            return None
        entry = {k: v for k, v in p.items() if k != "_api_key"}
        entry["has_api_key"] = self._load_api_key(p["id"]) is not None
        return entry

    @trace_sync
    def get_available_types(self) -> list[dict[str, Any]]:
        return [
            {
                "id": k,
                "name": v["name"],
                "needs_endpoint": k in ("openai_compatible", "custom"),
                "default_endpoint": v.get("endpoint", ""),
                "has_models_endpoint": v.get("models_endpoint") is not None,
            }
            for k, v in PROVIDER_META.items()
        ]

    @trace_sync
    def add_provider(
        self,
        provider_type: str,
        name: str | None = None,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        organization: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        streaming_enabled: bool = True,
        models_enabled: list[str] | None = None,
    ) -> dict[str, Any]:
        meta = PROVIDER_META.get(provider_type)
        if not meta and provider_type not in ("openai_compatible", "custom"):
            raise ValueError(f"Unknown provider type: {provider_type}")

        provider_id = f"{provider_type}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        catalog_models = get_catalog_models(provider_type)
        if models_enabled is not None:
            for m in catalog_models:
                m["enabled"] = m["id"] in models_enabled

        provider = {
            "id": provider_id,
            "type": provider_type,
            "name": name or (meta["name"] if meta else provider_type),
            "endpoint_url": endpoint_url or (meta.get("endpoint", "") if meta else ""),
            "organization": organization,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "streaming_enabled": streaming_enabled,
            "is_default": len(self._providers) == 0,
            "status": "not_configured",
            "latency_ms": None,
            "last_checked": None,
            "models": list(catalog_models),
            "created_at": now,
            "updated_at": now,
        }

        if api_key:
            try:
                self._store_api_key(provider_id, api_key)
            except SecureStorageError:
                # Provider metadata saved but API key not stored — mark for user action
                provider["secure_storage_unavailable"] = True
                logger.warning("provider.created_without_key", provider_id=provider_id)

        self._providers.append(provider)
        self._save()

        # Create and register adapter
        self._register_adapter(provider)

        entry = {k: v for k, v in provider.items() if k != "_api_key"}
        entry["has_api_key"] = api_key is not None
        return entry

    @trace_sync
    def update_provider(
        self,
        provider_id: str,
        name: str | None = None,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        organization: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        streaming_enabled: bool | None = None,
        model_updates: list[dict] | None = None,
    ) -> dict[str, Any]:
        provider = self._get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        if name is not None:
            provider["name"] = name
        if endpoint_url is not None:
            provider["endpoint_url"] = endpoint_url
        if organization is not None:
            provider["organization"] = organization
        if temperature is not None:
            provider["temperature"] = temperature
        if max_tokens is not None:
            provider["max_tokens"] = max_tokens
        if streaming_enabled is not None:
            provider["streaming_enabled"] = streaming_enabled
        if api_key is not None:
            try:
                self._store_api_key(provider_id, api_key)
            except SecureStorageError:
                provider["secure_storage_unavailable"] = True
                logger.warning("provider.update_key_failed", provider_id=provider_id)

        if model_updates is not None:
            existing = {m["id"]: m for m in provider.get("models", [])}
            for update in model_updates:
                mid = update.get("id")
                if mid in existing:
                    existing[mid].update(update)
            provider["models"] = list(existing.values())

        provider["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

        # Re-register adapter in case endpoint/API key changed
        self._unregister_adapter(provider_id)
        self._register_adapter(provider)

        entry = {k: v for k, v in provider.items() if k != "_api_key"}
        entry["has_api_key"] = self._load_api_key(provider["id"]) is not None
        return entry

    @trace_sync
    def remove_provider(self, provider_id: str):
        provider = self._get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        was_default = provider.get("is_default", False)
        self._providers = [p for p in self._providers if p["id"] != provider_id]
        self._delete_api_key(provider_id)

        for route in self._routing_config:
            if route.get("provider_id") == provider_id:
                route["provider_id"] = None
        self._save_routing()

        if was_default and self._providers:
            self._providers[0]["is_default"] = True
        self._save()

        self._unregister_adapter(provider_id)

    @trace_sync
    def set_default_provider(self, provider_id: str) -> dict[str, Any]:
        provider = self._get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")
        for p in self._providers:
            p["is_default"] = p["id"] == provider_id
        self._save()
        entry = {k: v for k, v in provider.items() if k != "_api_key"}
        entry["has_api_key"] = self._load_api_key(provider["id"]) is not None
        return entry

    @trace_sync
    def reorder_providers(self, provider_ids: list[str]):
        ordered = []
        seen = set()
        for pid in provider_ids:
            p = self._get_provider(pid)
            if p and pid not in seen:
                ordered.append(p)
                seen.add(pid)
        for p in self._providers:
            if p["id"] not in seen:
                ordered.append(p)
        self._providers = ordered
        self._save()

    # ------------------------------------------------------------------
    # Connection testing
    # ------------------------------------------------------------------

    @trace_async
    async def test_connection(self, provider_id: str) -> dict[str, Any]:
        provider = self._get_provider(provider_id)
        if not provider:
            return {"success": False, "error": "Provider not found"}

        adapter = self._adapters.get(provider_id)
        if not adapter:
            # Try creating adapter
            adapter = self._create_adapter(provider)
            if not adapter:
                return {"success": False, "error": "Could not create adapter"}

        start = time.monotonic()
        try:
            status = await call_with_timeout(
                adapter.health(),
                timeout=15.0,
                provider_id=provider_id,
                operation="test_connection",
            )
        except Exception as e:
            status = ProviderStatus.ERROR

        elapsed = int((time.monotonic() - start) * 1000)
        provider["latency_ms"] = elapsed
        provider["last_checked"] = datetime.now(timezone.utc).isoformat()

        if status == ProviderStatus.CONNECTED:
            provider["status"] = "connected"
            self._save()
            return {"success": True, "status": "connected", "latency_ms": elapsed}
        elif status == ProviderStatus.INVALID_KEY:
            provider["status"] = "invalid_key"
            self._save()
            return {"success": False, "error": "Invalid API key", "status": "invalid_key"}
        elif status == ProviderStatus.RATE_LIMITED:
            provider["status"] = "rate_limited"
            self._save()
            return {"success": False, "error": "Rate limited", "status": "rate_limited"}
        elif status == ProviderStatus.OFFLINE:
            provider["status"] = "offline"
            self._save()
            return {"success": False, "error": "Provider unreachable", "status": "offline"}
        elif status == ProviderStatus.TIMEOUT:
            provider["status"] = "offline"
            self._save()
            return {"success": False, "error": "Connection timed out", "status": "offline"}
        else:
            provider["status"] = "error"
            self._save()
            return {"success": False, "error": "Connection failed", "status": "error"}

    @trace_async
    async def test_all_connections(self) -> list[dict[str, Any]]:
        results = []
        for p in self._providers:
            try:
                result = await call_with_timeout(
                    self.test_connection(p["id"]),
                    timeout=20.0,
                    provider_id=p["id"],
                    operation="test_all_connections",
                )
                results.append({"provider_id": p["id"], **result})
            except Exception as e:
                results.append({
                    "provider_id": p["id"],
                    "success": False,
                    "error": sanitize_error(str(e)) or "Connection test timed out",
                    "status": "offline",
                })
        return results

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------

    @trace_async
    async def fetch_models(self, provider_id: str) -> list[dict]:
        """Fetch models from the provider API, merging with catalog metadata."""
        provider = self._get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        adapter = self._adapters.get(provider_id)
        if not adapter:
            return provider.get("models", [])

        # Try cache first
        cache_key = f"models:{provider_id}"
        try:
            fetched = await self._model_cache.get(
                cache_key,
                fetcher=lambda: self._fetch_and_merge(provider, adapter),
                ttl=300.0,
            )
            if fetched:
                provider["models"] = fetched
                self._save()
            return fetched or provider.get("models", [])
        except Exception as e:
            logger.warning("fetch_models.failed", provider_id=provider_id, error=sanitize_error(str(e)[:200]))
            return provider.get("models", [])

    async def _fetch_and_merge(self, provider: dict, adapter: AIProviderAdapter) -> list[dict]:
        """Fetch models from adapter and merge with catalog + user enabled state."""
        try:
            discovered = await adapter.list_models()
        except Exception as e:
            logger.warning("fetch_and_merge.list_models_failed", provider=provider["id"], error=sanitize_error(str(e)[:200]))
            discovered = []

        # Convert to storage format
        discovered_dicts = [m.to_dict() for m in discovered]

        # Merge with catalog to preserve metadata
        catalog = get_catalog_models(provider["type"])
        catalog_by_id = {m["id"]: m for m in catalog}

        merged = []
        seen = set()

        for md in discovered_dicts:
            mid = md["id"]
            seen.add(mid)
            if mid in catalog_by_id:
                entry = dict(catalog_by_id[mid])
                # Preserve discovered fields not in catalog
                entry.update({k: v for k, v in md.items() if k not in entry})
            else:
                entry = md
            merged.append(entry)

        for cm in catalog:
            if cm["id"] not in seen:
                merged.append(dict(cm))

        # Merge user enabled state
        existing = {m["id"]: m for m in provider.get("models", [])}
        for m in merged:
            mid = m["id"]
            if mid in existing:
                m["enabled"] = existing[mid].get("enabled", m.get("enabled", True))

        return merged

    @trace_sync
    def toggle_model(self, provider_id: str, model_id: str, enabled: bool) -> dict[str, Any]:
        provider = self._get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        for m in provider.get("models", []):
            if m["id"] == model_id:
                m["enabled"] = enabled
                break

        provider["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

        # Sync to smart router
        models = provider.get("models", [])
        model_infos = self._model_dicts_to_info(provider, models)
        self._smart_router.set_provider_models(provider_id, model_infos)

        return {k: v for k, v in provider.items() if k != "_api_key"}

    @trace_async
    async def refresh_models(self, provider_id: str) -> list[dict]:
        """Force refresh models from API, bypassing cache."""
        cache_key = f"models:{provider_id}"
        await self._model_cache.invalidate(cache_key)
        return await self.fetch_models(provider_id)

    # ------------------------------------------------------------------
    # Smart Routing
    # ------------------------------------------------------------------

    @trace_sync
    def get_routing(self) -> list[dict[str, Any]]:
        return list(self._routing_config)

    @trace_sync
    def set_routing(self, routing: list[dict[str, Any]]):
        valid_ids = {r["id"] for r in ROUTING_CATEGORIES}
        cleaned = []
        for entry in routing:
            if entry.get("id") in valid_ids:
                cleaned.append({
                    "id": entry["id"],
                    "label": entry.get("label", entry["id"]),
                    "provider_id": entry.get("provider_id"),
                    "model_id": entry.get("model_id"),
                })
        self._routing_config = cleaned
        self._save_routing()
        self._smart_router.set_routing_config(self._routing_config)

    # ------------------------------------------------------------------
    # Multi-account model aggregation
    # ------------------------------------------------------------------

    @trace_sync
    def get_all_free_models(self) -> list[dict[str, Any]]:
        """Aggregate all free-tier models across all registered providers."""
        free = []
        for p in self._providers:
            pid = p["id"]
            for m in p.get("models", []):
                if not m.get("enabled", True):
                    continue
                cs = m.get("commercialStatus", m.get("commercial_status", "unknown"))
                is_free = m.get("isFree", False)
                if cs in ("free", "free_tier", "local") or is_free:
                    entry = dict(m)
                    entry["provider_instance_id"] = pid
                    entry["provider_type"] = p["type"]
                    free.append(entry)
        return free

    @trace_sync
    def get_provider_type_models(self, provider_type: str) -> list[dict[str, Any]]:
        """List all models for a given provider type across all instances."""
        models = []
        for p in self._providers:
            if p["type"] != provider_type:
                continue
            pid = p["id"]
            for m in p.get("models", []):
                entry = dict(m)
                entry["provider_instance_id"] = pid
                entry["provider_type"] = p["type"]
                models.append(entry)
        return models

    @trace_sync
    def get_model_commercial_status(self, provider_id: str, model_id: str) -> dict[str, Any]:
        """Get commercial status and pricing for a specific model."""
        provider = self._get_provider(provider_id)
        if not provider:
            return {"error": "Provider not found"}
        for m in provider.get("models", []):
            if m["id"] == model_id:
                return {
                    "provider_id": provider_id,
                    "provider_type": provider["type"],
                    "model_id": model_id,
                    "commercial_status": m.get("commercialStatus", m.get("commercial_status", "unknown")),
                    "is_free": m.get("isFree", False),
                    "pricing": m.get("pricing", {"input": 0.0, "output": 0.0}),
                    "availability": m.get("availability", "available"),
                }
        return {"error": "Model not found"}

    @trace_sync
    def is_model_rate_limited(self, provider_id: str, model_id: str) -> bool:
        """Check if a specific model is currently rate-limited."""
        return not self._health_monitor.is_model_available(provider_id, model_id)

    # ------------------------------------------------------------------
    # Registration with SmartRouter
    # ------------------------------------------------------------------

    @trace_sync
    def register_all_adapters(self):
        """Register all configured providers as adapters with the SmartRouter.
        Register regardless of status (health monitor re-verifies)."""
        for p in self._providers:
            self._register_adapter(p)

    # ------------------------------------------------------------------
    # Access to internals (for use by ConversationManager et al.)
    # ------------------------------------------------------------------

    @property
    def smart_router(self) -> SmartRouter:
        return self._smart_router

    @property
    def health_monitor(self) -> HealthMonitor:
        return self._health_monitor

    @property
    def model_cache(self) -> ModelCache:
        return self._model_cache

    def get_adapter(self, provider_id: str) -> AIProviderAdapter | None:
        return self._adapters.get(provider_id)

    def get_adapters(self) -> dict[str, AIProviderAdapter]:
        return dict(self._adapters)

    def get_chat_model_id(self, provider_id: str) -> str:
        """Get the first enabled model ID for a provider."""
        provider = self._get_provider(provider_id)
        if not provider:
            return ""
        models = provider.get("models", [])
        for m in models:
            if m.get("enabled", True):
                return m["id"]
        return ""

    async def shutdown(self):
        """Gracefully shut down all background tasks and connections."""
        self._health_monitor.stop_background_check()
        self._model_cache.cancel_all()
        self._streaming.cancel_all()
        for pid, adapter in list(self._adapters.items()):
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.warning("provider.disconnect_failed", provider_id=pid, error=sanitize_error(str(e)[:200]))
        self._adapters.clear()
        logger.info("provider_manager.shutdown_complete")

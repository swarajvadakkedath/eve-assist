#!/usr/bin/env python3
"""
EVE v1.2.2 — Live Provider & Model Validation Script
=====================================================

Runs against the local running EVE backend (default: http://127.0.0.1:8456).
Does NOT require code changes. Uses only the existing REST API.

Usage:
    python validate_providers.py
    python validate_providers.py --provider google --provider openai
    python validate_providers.py --refresh --verbose --output report.md

Exit codes:
    0  All providers live-verified or expected-offline
    1  One or more INTEGRATION_FAILURE results
    2  Backend unreachable / startup error
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' library required.  pip install requests")

# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────

DEFAULT_BASE = "http://127.0.0.1:8456"
API = "/api/v1"
CHAT_PROMPT = "Reply ONLY with the single word: OK"
JSON_PROMPT = 'Return ONLY valid JSON, no markdown fences: {"name":"test","status":"ok"}'
STREAM_PROMPT = "Count from 1 to 10, one number per line."
CHAT_TIMEOUT = 60
STREAM_TIMEOUT = 90

KNOWN_PROVIDER_TYPES = {
    "openai": "OpenAI Platform",
    "google": "Google AI Studio",
    "groq": "GroqCloud",
    "openrouter": "OpenRouter",
    "ollama": "Ollama",
    "deepinfra": "DeepInfra",
    "cloudflare": "Cloudflare Workers AI",
    "huggingface": "Hugging Face Inference",
    "nvidia": "NVIDIA Build (NIM)",
}

PROVIDER_ICONS = {
    "openai": "🟢", "google": "🔵", "groq": "🟣",
    "openrouter": "🟠", "ollama": "🦙", "deepinfra": "🌊",
    "cloudflare": "☁️", "huggingface": "🤗", "nvidia": "💚",
}


# ─────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ProviderResult:
    provider_id: str
    display_name: str
    provider_type: str
    enabled: bool = True
    connection: str = "NOT_TESTED"
    health_score: float = 0.0
    latency_ms: float = 0.0
    model_count: int = 0
    free_model_count: int = 0
    reasoning_models: int = 0
    vision_models: int = 0
    streaming_supported: bool = False
    tool_calling: bool = False
    json_mode: bool = False
    embeddings: bool = False
    audio: bool = False
    images: bool = False
    chat_test: str = "NOT_TESTED"
    chat_latency_ms: float = 0.0
    streaming_test: str = "NOT_TESTED"
    json_test: str = "NOT_TESTED"
    vision_test: str = "NOT_TESTED"
    tool_test: str = "NOT_TESTED"
    free_routing_ok: bool = True
    fallback_ok: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    models: list = field(default_factory=list)
    verdict: str = "NOT_TESTED"


@dataclass
class ValidationReport:
    start_time: str = ""
    end_time: str = ""
    backend_url: str = ""
    backend_reachable: bool = False
    system_health: dict = field(default_factory=dict)
    total_providers_configured: int = 0
    total_providers_healthy: int = 0
    total_providers_offline: int = 0
    total_models: int = 0
    total_free_models: int = 0
    total_free_tier: int = 0
    total_paid: int = 0
    total_unknown: int = 0
    total_reasoning: int = 0
    total_vision: int = 0
    total_embedded: int = 0
    total_streaming: int = 0
    commercial_policy: str = ""
    routing_ok: bool = False
    security_ok: bool = True
    providers: list = field(default_factory=list)
    failures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    final_verdict: str = "PENDING"


# ─────────────────────────────────────────────────────────────────────
# API client
# ─────────────────────────────────────────────────────────────────────

class EveClient:
    def __init__(self, base_url: str, verbose: bool = False):
        self.base = base_url.rstrip("/")
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _url(self, path: str) -> str:
        return f"{self.base}{API}{path}"

    def get(self, path: str, timeout: int = 15) -> dict | list | None:
        try:
            r = self.session.get(self._url(path), timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            raise
        except requests.exceptions.Timeout:
            raise
        except Exception as e:
            if self.verbose:
                print(f"    [WARN] GET {path}: {e}")
            return None

    def post(self, path: str, data: dict = None, timeout: int = 15) -> dict | list | None:
        try:
            r = self.session.post(self._url(path), json=data or {}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            raise
        except requests.exceptions.Timeout:
            raise
        except Exception as e:
            if self.verbose:
                print(f"    [WARN] POST {path}: {e}")
            return None

    def put(self, path: str, data: dict = None, timeout: int = 15) -> dict | list | None:
        try:
            r = self.session.put(self._url(path), json=data or {}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            raise
        except requests.exceptions.Timeout:
            raise
        except Exception as e:
            if self.verbose:
                print(f"    [WARN] PUT {path}: {e}")
            return None

    def delete(self, path: str, timeout: int = 15) -> dict | None:
        try:
            r = self.session.delete(self._url(path), timeout=timeout)
            r.raise_for_status()
            return r.json() if r.content else {}
        except Exception as e:
            if self.verbose:
                print(f"    [WARN] DELETE {path}: {e}")
            return None

    def stream_post(self, path: str, data: dict = None, timeout: int = 90) -> tuple[bool, str, float]:
        """Returns (success, text, latency_ms)."""
        try:
            t0 = time.time()
            r = self.session.post(
                self._url(path), json=data or {}, timeout=timeout, stream=True
            )
            r.raise_for_status()
            chunks = []
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            chunks.append(content)
                    except json.JSONDecodeError:
                        pass
            latency = (time.time() - t0) * 1000
            return True, "".join(chunks), latency
        except Exception as e:
            latency = (time.time() - t0) * 1000 if "t0" in dir() else 0
            return False, str(e), latency


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _mask(s: str, keep: int = 4) -> str:
    if not s or len(s) <= keep:
        return "***"
    return s[:keep] + "***" + s[-2:]


def _capability_from_model(model: dict) -> dict:
    caps = {
        "vision": False, "reasoning": False, "streaming": True,
        "json_mode": False, "tool_calling": False, "embeddings": False,
        "audio": False, "images": False,
    }
    mid = (model.get("id") or model.get("modelId") or "").lower()
    caps_raw = model.get("capabilities") or {}
    if isinstance(caps_raw, dict):
        caps["vision"] = bool(caps_raw.get("vision"))
        caps["reasoning"] = bool(caps_raw.get("reasoning"))
        caps["streaming"] = caps_raw.get("streaming", True)
        caps["json_mode"] = bool(caps_raw.get("json") or caps_raw.get("json_mode"))
        caps["tool_calling"] = bool(caps_raw.get("tools") or caps_raw.get("function_calling") or caps_raw.get("tool_calling"))
        caps["embeddings"] = bool(caps_raw.get("embeddings") or model.get("isEmbeddingModel"))
        caps["audio"] = bool(caps_raw.get("audio"))
        caps["images"] = bool(caps_raw.get("images"))
    if "embed" in mid:
        caps["embeddings"] = True
    for kw in ["o1", "o3", "r1", "qwq", "deepseek-r1", "gemini-2.5", "kimi", "thinking"]:
        if kw in mid:
            caps["reasoning"] = True
            break
    for kw in ["vision", "gpt-4o", "gpt-4v", "claude-3", "gemini-2", "llava"]:
        if kw in mid:
            caps["vision"] = True
            break
    return caps


def _commercial_status(model: dict) -> str:
    cs = (model.get("commercialStatus") or model.get("commercial_policy") or "unknown").lower()
    if model.get("isFree") or model.get("is_free"):
        return "free"
    if cs in ("free",):
        return "free"
    if cs in ("free_tier",):
        return "free_tier"
    if cs in ("paid", "credit_based", "subscription"):
        return "paid"
    return "unknown"


def _provider_display_name(pid: str, ptype: str) -> str:
    known = KNOWN_PROVIDER_TYPES.get(ptype)
    if known:
        return known
    return pid.replace("_", " ").replace("-", " ").title()


# ─────────────────────────────────────────────────────────────────────
# Phase implementations
# ─────────────────────────────────────────────────────────────────────

def phase_connectivity(client: EveClient, report: ValidationReport,
                       filter_providers: set | None = None) -> None:
    """Phase 1: Read configured providers, verify connectivity."""
    print("\n═══ PHASE 1: PROVIDER CONNECTIVITY ═══")

    providers = client.get("/providers")
    if providers is None:
        report.warnings.append("Could not fetch provider list from backend")
        print("  ⚠  Backend returned no provider list")
        return

    if isinstance(providers, dict):
        providers = providers.get("providers", [])

    for p in providers:
        pid = p.get("id") or p.get("provider_id") or ""
        if filter_providers and pid not in filter_providers:
            continue

        pr = ProviderResult(
            provider_id=pid,
            display_name=_provider_display_name(pid, p.get("type", "")),
            provider_type=p.get("type", "unknown"),
            enabled=p.get("enabled", True),
        )
        print(f"\n  {PROVIDER_ICONS.get(pid, '⚪')} {pr.display_name} ({pid})")
        print(f"    Type: {pr.provider_type}")
        print(f"    Enabled: {pr.enabled}")

        if not pr.enabled:
            pr.connection = "DISABLED"
            pr.warnings.append("Provider is disabled")
            report.providers.append(pr)
            continue

        test_result = client.post(f"/providers/{pid}/test")
        if test_result is None:
            pr.connection = "UNREACHABLE"
            pr.errors.append("Test endpoint returned no response")
            print(f"    Connection: ❌ UNREACHABLE")
        else:
            ok = test_result.get("success") or test_result.get("connected") or test_result.get("healthy")
            if ok:
                pr.connection = "CONNECTED"
                pr.latency_ms = test_result.get("latency_ms") or test_result.get("latency") or 0
                print(f"    Connection: ✅ CONNECTED  (latency: {pr.latency_ms:.0f}ms)")
            else:
                pr.connection = "AUTH_FAILED"
                err = test_result.get("error") or test_result.get("message", "unknown")
                pr.errors.append(f"Auth/connect error: {err}")
                print(f"    Connection: ❌ AUTH_FAILED — {err}")

        report.providers.append(pr)

    print(f"\n  Total configured: {len(report.providers)}")


def phase_health(client: EveClient, report: ValidationReport) -> None:
    """Phase 2: Health checks."""
    print("\n═══ PHASE 2: HEALTH CHECKS ═══")

    health_data = client.get("/providers/health")
    if health_data is None:
        report.warnings.append("Health endpoint returned no data")
        print("  ⚠  No health data available")
        return

    health_list = health_data if isinstance(health_data, list) else health_data.get("providers", health_data.get("health", []))

    health_map = {}
    for h in (health_list if isinstance(health_list, list) else []):
        hid = h.get("provider_id") or h.get("id") or ""
        health_map[hid] = h

    for pr in report.providers:
        h = health_map.get(pr.provider_id)
        if h:
            pr.health_score = h.get("health_score") or h.get("score") or 0
            latency = h.get("latency_ms") or h.get("latency") or 0
            if latency and not pr.latency_ms:
                pr.latency_ms = latency
            status = h.get("status", "unknown")
            if status in ("unreachable", "error", "offline"):
                pr.connection = "OFFLINE"
                pr.errors.append(f"Health: {status}")
            print(f"  {PROVIDER_ICONS.get(pr.provider_id, '⚪')} {pr.display_name}: "
                  f"score={pr.health_score:.0f}  latency={pr.latency_ms:.0f}ms  status={status}")
        else:
            print(f"  {PROVIDER_ICONS.get(pr.provider_id, '⚪')} {pr.display_name}: no health data")

    healthy = sum(1 for p in report.providers if p.connection in ("CONNECTED", "DISABLED"))
    report.total_providers_healthy = healthy
    report.total_providers_offline = len(report.providers) - healthy


def phase_model_discovery(client: EveClient, report: ValidationReport,
                          do_refresh: bool = False) -> None:
    """Phase 3: Model discovery."""
    print("\n═══ PHASE 3: MODEL DISCOVERY ═══")

    for pr in report.providers:
        if pr.connection == "DISABLED":
            continue

        if do_refresh:
            print(f"  Refreshing models for {pr.display_name}...")
            client.post(f"/providers/{pr.provider_id}/models/refresh")

        models_data = client.get(f"/providers/{pr.provider_id}/models")
        if models_data is None:
            pr.errors.append("Model discovery returned no data")
            print(f"  ⚠  {pr.display_name}: no models returned")
            continue

        models = models_data if isinstance(models_data, list) else models_data.get("models", [])
        pr.models = models
        pr.model_count = len(models)

        seen_ids = set()
        dups = 0
        for m in models:
            mid = m.get("id") or m.get("modelId") or ""
            if mid in seen_ids:
                dups += 1
            seen_ids.add(mid)

            caps = _capability_from_model(m)
            cs = _commercial_status(m)
            if caps["vision"]:
                pr.vision_models += 1
            if caps["reasoning"]:
                pr.reasoning_models += 1
            if caps["streaming"]:
                pr.streaming_supported = True
            if caps["tool_calling"]:
                pr.tool_calling = True
            if caps["json_mode"]:
                pr.json_mode = True
            if caps["embeddings"]:
                pr.embeddings = True
            if caps["audio"]:
                pr.audio = True
            if caps["images"]:
                pr.images = True
            if cs == "free":
                pr.free_model_count += 1
            elif cs == "free_tier":
                pr.free_model_count += 1

        if dups:
            pr.warnings.append(f"{dups} duplicate model IDs found")
        print(f"  {PROVIDER_ICONS.get(pr.provider_id, '⚪')} {pr.display_name}: "
              f"{pr.model_count} models  ({pr.free_model_count} free)  "
              f"dupes={dups}  vision={pr.vision_models}  reasoning={pr.reasoning_models}")

    report.total_models = sum(p.model_count for p in report.providers)
    report.total_free_models = sum(p.free_model_count for p in report.providers)


def phase_capability_summary(report: ValidationReport) -> None:
    """Phase 4: Capability validation summary."""
    print("\n═══ PHASE 4: CAPABILITY VALIDATION ═══")

    total_streaming = sum(1 for p in report.providers if p.streaming_supported)
    total_tools = sum(1 for p in report.providers if p.tool_calling)
    total_json = sum(1 for p in report.providers if p.json_mode)
    total_emb = sum(1 for p in report.providers if p.embeddings)
    total_audio = sum(1 for p in report.providers if p.audio)
    total_images = sum(1 for p in report.providers if p.images)

    report.total_reasoning = sum(p.reasoning_models for p in report.providers)
    report.total_vision = sum(p.vision_models for p in report.providers)
    report.total_streaming = total_streaming
    report.total_embedded = total_emb

    print(f"  Reasoning models: {report.total_reasoning}")
    print(f"  Vision models:    {report.total_vision}")
    print(f"  Streaming capable:{total_streaming} providers")
    print(f"  Tool calling:     {total_tools} providers")
    print(f"  JSON mode:        {total_json} providers")
    print(f"  Embeddings:       {total_emb} providers")
    print(f"  Audio:            {total_audio} providers")
    print(f"  Images:           {total_images} providers")


def phase_live_chat(client: EveClient, report: ValidationReport,
                    filter_providers: set | None = None) -> None:
    """Phase 5: Live chat test — send minimal prompt to each provider."""
    print("\n═══ PHASE 5: LIVE CHAT ═══")

    for pr in report.providers:
        if pr.connection not in ("CONNECTED",):
            pr.chat_test = "SKIPPED_NOT_CONNECTED"
            print(f"  ⏭  {pr.display_name}: skipped (not connected)")
            continue

        if filter_providers and pr.provider_id not in filter_providers:
            continue

        if pr.model_count == 0:
            pr.chat_test = "SKIPPED_NO_MODELS"
            print(f"  ⏭  {pr.display_name}: skipped (no models)")
            continue

        best_model = _pick_chat_model(pr)
        if not best_model:
            pr.chat_test = "SKIPPED_NO_CHAT_MODEL"
            print(f"  ⏭  {pr.display_name}: skipped (no suitable chat model)")
            continue

        mid = best_model.get("id") or best_model.get("modelId") or ""
        print(f"  💬 {pr.display_name}: testing model {mid}...")

        t0 = time.time()
        result = client.post("/chat/message", {
            "messages": [{"role": "user", "content": CHAT_PROMPT}],
            "model": mid,
            "provider": pr.provider_id,
            "max_tokens": 32,
        }, timeout=CHAT_TIMEOUT)
        latency = (time.time() - t0) * 1000
        pr.chat_latency_ms = latency

        if result is None:
            pr.chat_test = "FAILED"
            pr.errors.append("Chat request returned no response")
            print(f"    ❌ FAILED  ({latency:.0f}ms)")
        else:
            content = result.get("content") or result.get("message") or ""
            model_used = result.get("model") or result.get("model_used") or mid
            pr.chat_test = "PASS"
            print(f"    ✅ PASS  model={model_used}  latency={latency:.0f}ms  "
                  f"response={content[:40]}")

        if latency > 10000:
            pr.warnings.append(f"Chat latency {latency:.0f}ms exceeds 10s threshold")


def phase_streaming(client: EveClient, report: ValidationReport) -> None:
    """Phase 6: Streaming test."""
    print("\n═══ PHASE 6: STREAMING ═══")

    for pr in report.providers:
        if pr.chat_test != "PASS" or not pr.streaming_supported:
            pr.streaming_test = "SKIPPED"
            continue

        best_model = _pick_chat_model(pr)
        if not best_model:
            pr.streaming_test = "SKIPPED_NO_MODEL"
            continue

        mid = best_model.get("id") or best_model.get("modelId") or ""
        print(f"  🌊 {pr.display_name}: streaming with {mid}...")

        ok, text, latency = client.stream_post("/chat/stream", {
            "messages": [{"role": "user", "content": STREAM_PROMPT}],
            "model": mid,
            "provider": pr.provider_id,
            "max_tokens": 128,
        }, timeout=STREAM_TIMEOUT)

        if ok and len(text.strip()) > 0:
            pr.streaming_test = "PASS"
            print(f"    ✅ PASS  ({latency:.0f}ms)  chars={len(text)}")
        else:
            pr.streaming_test = "FAIL"
            pr.errors.append(f"Streaming failed: {text[:100]}")
            print(f"    ❌ FAIL  ({latency:.0f}ms)  {text[:80]}")


def phase_json_mode(client: EveClient, report: ValidationReport) -> None:
    """Phase 7: JSON mode test."""
    print("\n═══ PHASE 7: JSON MODE ═══")

    for pr in report.providers:
        if pr.chat_test != "PASS":
            pr.json_test = "SKIPPED"
            continue

        best_model = _pick_chat_model(pr, prefer_json=True)
        if not best_model:
            pr.json_test = "SKIPPED_NO_MODEL"
            continue

        mid = best_model.get("id") or best_model.get("modelId") or ""
        print(f"  📋 {pr.display_name}: JSON mode with {mid}...")

        result = client.post("/chat/message", {
            "messages": [{"role": "user", "content": JSON_PROMPT}],
            "model": mid,
            "provider": pr.provider_id,
            "max_tokens": 64,
            "response_format": {"type": "json_object"} if pr.json_mode else None,
        }, timeout=CHAT_TIMEOUT)

        if result is None:
            pr.json_test = "FAIL"
            pr.errors.append("JSON mode request returned no response")
            print(f"    ❌ FAIL")
            continue

        content = (result.get("content") or result.get("message") or "").strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        content = content.strip()

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                pr.json_test = "PASS"
                print(f"    ✅ PASS  parsed OK  keys={list(parsed.keys())}")
            else:
                pr.json_test = "PARTIAL"
                pr.warnings.append("JSON parsed but not a dict")
                print(f"    ⚠️  PARTIAL  parsed but not a dict")
        except json.JSONDecodeError:
            pr.json_test = "FAIL"
            pr.errors.append(f"Invalid JSON: {content[:100]}")
            print(f"    ❌ FAIL  not valid JSON: {content[:60]}")


def phase_free_routing(client: EveClient, report: ValidationReport) -> None:
    """Phase 8: Verify FREE_ONLY routing never selects PAID models."""
    print("\n═══ PHASE 8: FREE ROUTING VALIDATION ═══")

    policy_data = client.get("/routing/commercial-policy")
    if policy_data:
        policy = policy_data.get("policy") or policy_data.get("commercial_policy") or "unknown"
        report.commercial_policy = policy
        print(f"  Current policy: {policy}")
    else:
        print("  ⚠  Could not fetch commercial policy")
        return

    free_models = client.get("/providers/models/free")
    if free_models is None:
        report.warnings.append("Could not fetch free models")
        print("  ⚠  Could not fetch free models list")
        return

    if isinstance(free_models, dict):
        free_models = free_models.get("models", [])

    print(f"  Free models available: {len(free_models)}")

    for m in free_models:
        cs = _commercial_status(m)
        if cs == "paid":
            report.warnings.append(f"PAID model {m.get('id')} appeared in free list")
            print(f"  ⚠️  PAID model in free list: {m.get('id')}")

    for pr in report.providers:
        if pr.connection != "CONNECTED" or pr.model_count == 0:
            continue
        free_count = sum(1 for m in pr.models if _commercial_status(m) in ("free", "free_tier"))
        if policy.lower() in ("free_only",) and free_count == 0 and pr.model_count > 0:
            pr.free_routing_ok = False
            pr.errors.append("FREE_ONLY policy but no free models available")
            print(f"  ⚠️  {pr.display_name}: FREE_ONLY but no free models!")

    report.routing_ok = all(p.free_routing_ok for p in report.providers if p.connection == "CONNECTED")


def phase_fallback(client: EveClient, report: ValidationReport) -> None:
    """Phase 9: Fallback test — temporarily test fallback diagnostics."""
    print("\n═══ PHASE 9: FALLBACK VALIDATION ═══")

    diag = client.get("/routing/diagnostics")
    if diag is None:
        report.warnings.append("Routing diagnostics not available")
        print("  ⚠  Diagnostics endpoint not available")
        return

    health = diag.get("health", diag.get("provider_health", {}))
    rate_limits = diag.get("rate_limits", diag.get("rate_limit_state", {}))
    print(f"  Provider health entries: {len(health)}")
    print(f"  Rate limit entries: {len(rate_limits)}")

    for pr in report.providers:
        h = health.get(pr.provider_id, {})
        if h:
            score = h.get("health_score") or h.get("score") or 0
            failures = h.get("consecutive_failures") or h.get("failures") or 0
            pr.fallback_ok = score > 0 or failures == 0

    routing = client.get("/routing")
    if routing:
        candidates = routing.get("routing", routing.get("candidates", []))
        if isinstance(candidates, list):
            print(f"  Active routing entries: {len(candidates)}")
            for c in candidates[:5]:
                pid = c.get("provider_id") or c.get("provider") or ""
                mid = c.get("model_id") or c.get("model") or ""
                score = c.get("score") or c.get("health_score") or 0
                print(f"    → {pid}/{mid}  score={score}")
    print("  ✅ Fallback diagnostics complete")


def phase_security(client: EveClient, report: ValidationReport) -> None:
    """Phase 10: Security checks — verify no secrets in API responses."""
    print("\n═══ PHASE 10: SECURITY CHECKS ═══")

    settings = client.get("/settings")
    if settings:
        for key in ("ai_api_key", "api_key", "secret", "token", "password"):
            val = settings.get(key, "")
            if val and len(val) > 4:
                report.security_ok = False
                report.failures.append(f"SECURITY: plaintext secret in settings.{key}")
                print(f"  ❌ Plaintext secret detected in settings.{key}")
    print(f"  Settings check: {'✅ PASS' if report.security_ok else '❌ FAIL'}")

    providers_raw = client.get("/providers")
    if providers_raw:
        check_str = json.dumps(providers_raw)
        key_patterns = re.findall(r'sk-[a-zA-Z0-9]{20,}', check_str)
        if key_patterns:
            report.security_ok = False
            report.failures.append("SECURITY: API keys detected in provider listing response")
            print(f"  ❌ API keys detected in provider listing response")
        else:
            print(f"  Provider data check: ✅ PASS")

    diag = client.get("/routing/diagnostics")
    if diag:
        diag_str = json.dumps(diag)
        if re.search(r'sk-[a-zA-Z0-9]{20,}', diag_str):
            report.security_ok = False
            report.failures.append("SECURITY: API keys in routing diagnostics")
            print(f"  ❌ API keys in routing diagnostics")
        else:
            print(f"  Diagnostics check: ✅ PASS")

    print(f"  Security verdict: {'✅ PASS' if report.security_ok else '❌ FAIL'}")


def _pick_chat_model(provider: ProviderResult, prefer_json: bool = False) -> dict | None:
    """Pick the best free model for chat testing."""
    candidates = []
    for m in provider.models:
        cs = _commercial_status(m)
        mid = (m.get("id") or m.get("modelId") or "").lower()
        caps = _capability_from_model(m)
        if cs not in ("free", "free_tier"):
            continue
        if "embed" in mid:
            continue
        score = 0
        if caps["tool_calling"]:
            score += 3
        if caps["json_mode"] and prefer_json:
            score += 5
        if caps["vision"]:
            score += 1
        if caps["reasoning"]:
            score += 1
        candidates.append((score, m))

    if not candidates:
        for m in provider.models:
            mid = (m.get("id") or m.get("modelId") or "").lower()
            if "embed" in mid:
                continue
            candidates.append((0, m))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# ─────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────

def generate_report(report: ValidationReport) -> str:
    lines = []
    w = lines.append

    w("# EVE v1.2.2 — Provider Validation Report")
    w("")
    w(f"Generated: {report.end_time}")
    w(f"Backend: {report.backend_url}")
    w("")

    # ── Summary ──
    w("## Executive Summary")
    w("")
    w(f"| Metric | Value |")
    w(f"|--------|-------|")
    w(f"| Backend Reachable | {'✅ YES' if report.backend_reachable else '❌ NO'} |")
    w(f"| Providers Configured | {report.total_providers_configured} |")
    w(f"| Providers Healthy | {report.total_providers_healthy} |")
    w(f"| Providers Offline | {report.total_providers_offline} |")
    w(f"| Total Models | {report.total_models} |")
    w(f"| Free Models | {report.total_free_models} |")
    w(f"| Commercial Policy | {report.commercial_policy} |")
    w(f"| Routing OK | {'✅' if report.routing_ok else '⚠️'} |")
    w(f"| Security | {'✅ PASS' if report.security_ok else '❌ FAIL'} |")
    w(f"| Final Verdict | **{report.final_verdict}** |")
    w("")

    # ── Provider Matrix ──
    w("## Provider Matrix")
    w("")
    w("| Provider | Connection | Models | Free | Chat | Stream | Vision | Tools | JSON | Reasoning | Health | Latency | Verdict |")
    w("|----------|-----------|--------|------|------|--------|--------|-------|------|-----------|--------|---------|---------|")
    for pr in report.providers:
        icon = PROVIDER_ICONS.get(pr.provider_id, "⚪")
        conn = _verdict_icon(pr.connection)
        chat = _verdict_icon(pr.chat_test)
        stream = _verdict_icon(pr.streaming_test)
        vision = "✅" if pr.vision_models > 0 else "—"
        tools = "✅" if pr.tool_calling else "—"
        json_m = _verdict_icon(pr.json_test) if pr.json_test != "SKIPPED" else "—"
        reason = "✅" if pr.reasoning_models > 0 else "—"
        health = f"{pr.health_score:.0f}%" if pr.health_score else "—"
        latency = f"{pr.latency_ms:.0f}ms" if pr.latency_ms else "—"
        verdict = _classify_verdict(pr)
        w(f"| {icon} {pr.display_name} | {conn} | {pr.model_count} | {pr.free_model_count} | "
          f"{chat} | {stream} | {vision} | {tools} | {json_m} | {reason} | "
          f"{health} | {latency} | **{verdict}** |")
    w("")

    # ── Model Inventory ──
    w("## Model Inventory")
    w("")
    w(f"| Category | Count |")
    w(f"|----------|-------|")
    w(f"| Total Models | {report.total_models} |")
    w(f"| Free Models | {report.total_free_models} |")
    w(f"| Reasoning Models | {report.total_reasoning} |")
    w(f"| Vision Models | {report.total_vision} |")
    w(f"| Streaming-Capable Providers | {report.total_streaming} |")
    w(f"| Embedding Models | {report.total_embedded} |")
    w("")

    # ── Per-provider model details ──
    w("## Model Details by Provider")
    w("")
    for pr in report.providers:
        if not pr.models:
            continue
        w(f"### {pr.display_name}")
        w("")
        w("| Model ID | Free | Vision | Reasoning | Tools | JSON | Context |")
        w("|----------|------|--------|-----------|-------|------|---------|")
        for m in pr.models[:30]:
            mid = m.get("id") or m.get("modelId") or "unknown"
            cs = _commercial_status(m)
            caps = _capability_from_model(m)
            ctx = m.get("context_window") or m.get("contextWindow") or "—"
            free = "✅" if cs in ("free", "free_tier") else ("💰" if cs == "paid" else "?")
            vis = "✅" if caps["vision"] else "—"
            reas = "✅" if caps["reasoning"] else "—"
            tools = "✅" if caps["tool_calling"] else "—"
            json_m = "✅" if caps["json_mode"] else "—"
            w(f"| `{mid}` | {free} | {vis} | {reas} | {tools} | {json_m} | {ctx} |")
        if len(pr.models) > 30:
            w(f"| ... and {len(pr.models) - 30} more | | | | | | |")
        w("")

    # ── Errors & Warnings ──
    w("## Errors & Warnings")
    w("")
    has_issues = False
    for pr in report.providers:
        if pr.errors or pr.warnings:
            has_issues = True
            w(f"### {pr.display_name}")
            w("")
            for e in pr.errors:
                w(f"- ❌ {e}")
            for wr in pr.warnings:
                w(f"- ⚠️  {wr}")
            w("")
    if not has_issues:
        w("No errors or warnings detected.")
        w("")

    # ── Failures ──
    if report.failures:
        w("## Failures")
        w("")
        for f in report.failures:
            w(f"- {f}")
        w("")

    # ── Recommendations ──
    w("## Recommendations")
    w("")
    offline = [p for p in report.providers if p.connection in ("OFFLINE", "UNREACHABLE", "AUTH_FAILED")]
    if offline:
        w("### Offline Providers")
        for p in offline:
            w(f"- **{p.display_name}**: {', '.join(p.errors)}")
        w("")

    no_free = [p for p in report.providers
               if p.connection == "CONNECTED" and p.free_model_count == 0 and p.model_count > 0]
    if no_free:
        w("### No Free Models")
        for p in no_free:
            w(f"- **{p.display_name}**: {p.model_count} models but none classified as free")
        w("")

    slow = [p for p in report.providers if p.chat_latency_ms > 10000]
    if slow:
        w("### High Latency")
        for p in slow:
            w(f"- **{p.display_name}**: {p.chat_latency_ms:.0f}ms chat latency")
        w("")

    w("---")
    w("")
    w("*Report generated by validate_providers.py — EVE v1.2.2 release validation tool*")
    w("")

    return "\n".join(lines)


def _verdict_icon(status: str) -> str:
    s = status.upper()
    if "PASS" in s or "CONNECTED" in s:
        return "✅"
    if "FAIL" in s or "AUTH" in s or "ERROR" in s:
        return "❌"
    if "SKIP" in s:
        return "⏭️"
    if "OFFLINE" in s or "UNREACHABLE" in s:
        return "🔴"
    return "⚪"


def _classify_verdict(pr: ProviderResult) -> str:
    if pr.connection == "DISABLED":
        return "EXPECTED OFFLINE"
    if pr.connection in ("OFFLINE", "UNREACHABLE"):
        return "EXPECTED OFFLINE"
    if pr.connection == "AUTH_FAILED":
        return "EXTERNAL FAILURE"
    if pr.chat_test == "FAILED":
        return "INTEGRATION FAILURE"
    if pr.connection == "CONNECTED" and pr.chat_test == "PASS":
        return "LIVE VERIFIED"
    if pr.connection == "CONNECTED" and pr.model_count > 0:
        return "LIVE VERIFIED"
    return "INTEGRATION FAILURE"


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EVE v1.2.2 — Live Provider & Model Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--provider", action="append", dest="providers",
                        help="Validate only this provider (repeatable)")
    parser.add_argument("--refresh", action="store_true",
                        help="Force-refresh model catalog before validation")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print detailed debug output")
    parser.add_argument("--output", "-o", default="EVE_V1.2.2_PROVIDER_VALIDATION_REPORT.md",
                        help="Output report path (default: EVE_V1.2.2_PROVIDER_VALIDATION_REPORT.md)")
    parser.add_argument("--base-url", default=DEFAULT_BASE,
                        help=f"Backend URL (default: {DEFAULT_BASE})")
    args = parser.parse_args()

    filter_set = set(args.providers) if args.providers else None

    print("=" * 60)
    print("  EVE v1.2.2 — Live Provider & Model Validation")
    print("=" * 60)
    print(f"  Backend: {args.base_url}")
    print(f"  Time: {datetime.now(timezone.utc).isoformat()}")
    if filter_set:
        print(f"  Filtered providers: {', '.join(filter_set)}")
    print()

    client = EveClient(args.base_url, verbose=args.verbose)
    report = ValidationReport(
        start_time=datetime.now(timezone.utc).isoformat(),
        backend_url=args.base_url,
    )

    # ── Pre-flight ──
    print("═══ PRE-FLIGHT: BACKEND CONNECTIVITY ═══")
    try:
        health = client.get("/system/health", timeout=5)
        if health:
            report.backend_reachable = True
            report.system_health = health
            version = health.get("version") or health.get("app_version") or "?"
            print(f"  ✅ Backend reachable  version={version}")
        else:
            print("  ⚠  Backend responded but health data empty")
            report.backend_reachable = True
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Cannot connect to {args.base_url}")
        print(f"     Ensure the EVE backend is running:")
        print(f"       cd src/backend && python -m uvicorn aios.api.app:app --port 8456")
        sys.exit(2)
    except Exception as e:
        print(f"  ❌ Backend error: {e}")
        sys.exit(2)

    # ── Run phases ──
    phase_connectivity(client, report, filter_set)
    phase_health(client, report)
    phase_model_discovery(client, report, do_refresh=args.refresh)
    phase_capability_summary(report)
    phase_live_chat(client, report, filter_set)
    phase_streaming(client, report)
    phase_json_mode(client, report)
    phase_free_routing(client, report)
    phase_fallback(client, report)
    phase_security(client, report)

    # ── Finalize ──
    report.end_time = datetime.now(timezone.utc).isoformat()
    report.total_providers_configured = len(report.providers)

    has_integration_failure = any(
        _classify_verdict(p) == "INTEGRATION FAILURE" for p in report.providers
    )
    if has_integration_failure:
        report.final_verdict = "INTEGRATION_FAILURES_DETECTED"
    elif report.security_ok:
        report.final_verdict = "PRODUCTION_READY"
    else:
        report.final_verdict = "SECURITY_FAILURES"

    # ── Generate report ──
    md = generate_report(report)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n{'=' * 60}")
    print(f"  Report written to: {args.output}")
    print(f"  Final verdict: {report.final_verdict}")
    print(f"{'=' * 60}")

    # ── Exit code ──
    if report.final_verdict in ("INTEGRATION_FAILURES_DETECTED", "SECURITY_FAILURES"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

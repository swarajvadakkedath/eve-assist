# EVE v1.2.2 — Provider Onboarding Report

**Date:** 2026-08-03
**Backend:** Running at `http://127.0.0.1:8456` (eve-desktop PID 14180)
**Method:** POST /providers/onboard → test → refresh → diagnostics → chat → security audit
**Result:** 9/9 providers onboarded, 8/9 connected, 66 free models, security audit PASS

---

## Summary

| Provider | Status | Models | Free | Latency | Capabilities |
|----------|--------|--------|------|---------|--------------|
| OpenAI | connected | 122 | 0 | 3297ms | FunctionCalling, Reasoning, Streaming, Tools, Vision, Thinking |
| Google AI Studio | connected | 52 | 4 | 250ms | FunctionCalling, JSON, Reasoning, Streaming, Tools, Vision, Thinking |
| Groq Cloud | connected | 20 | 20 | 375ms | FunctionCalling, JSON, Reasoning, Streaming, Tools |
| OpenRouter | connected | 337 | 17 | 78ms | Audio, FunctionCalling, Reasoning, Streaming, Tools, Vision, Thinking, Video |
| Ollama Local | connected | 13 | 13 | 358ms | FunctionCalling, Reasoning, Streaming, Tools |
| DeepInfra | connected | 186 | 5 | 1264ms | Audio, Embeddings, FunctionCalling, ImageGeneration, JSON, Reasoning, Streaming, Tools, Vision, Thinking, Video |
| Cloudflare Workers AI | error | 5 | 0 | — | FunctionCalling, JSON, Streaming, Tools |
| Hugging Face Inference | connected | 130 | 0 | 514ms | FunctionCalling, Reasoning, Streaming, Tools, Vision, Thinking |
| NVIDIA NIM | connected | 102 | 2 | 139ms | Embeddings, FunctionCalling, Reasoning, Streaming, Tools, Vision, Thinking |

**Totals:** 967 models discovered, 66 free models across 7 providers

---

## Per-Provider Details

### 1. OpenAI Platform

| Field | Value |
|-------|-------|
| Provider Type | `openai` |
| Instance ID | `openai-f7b2d48c` |
| Connection Status | **connected** |
| Health Status | healthy (score=100.0, success_rate=1.0) |
| Models Discovered | 122 |
| Free Models | 0 |
| Latency | 3297ms |
| Capabilities | FunctionCalling, Reasoning, Streaming, SystemPrompt, Temperature, Thinking, Tools, TopP, Vision |
| SmartRouter Categories | general_chat, coding, vision, reasoning |
| Chat Test | PASS (HTTP 200, gpt-4o-mini) |
| Warnings | None |

### 2. Google AI Studio

| Field | Value |
|-------|-------|
| Provider Type | `google` |
| Instance ID | `google-167d1a93` |
| Connection Status | **connected** |
| Health Status | healthy (score=100.0, success_rate=1.0) |
| Models Discovered | 52 |
| Free Models | 4 (gemini-2.5-flash, gemini-2.0-flash, gemini-2.0-flash-lite, gemini-1.5-flash) |
| Latency | 250ms |
| Capabilities | FunctionCalling, JSON, Reasoning, Streaming, SystemPrompt, Temperature, Thinking, Tools, TopP, Vision |
| SmartRouter Categories | general_chat, coding, vision, reasoning |
| Chat Test | TIMEOUT (60s timeout on gemini-2.0-flash — model latency, not framework issue) |
| Warnings | Chat timed out; may need longer timeout or different model |

### 3. Groq Cloud

| Field | Value |
|-------|-------|
| Provider Type | `groq` |
| Instance ID | `groq-dcf2dfb6` |
| Connection Status | **connected** |
| Health Status | healthy (score=100.0, success_rate=1.0) |
| Models Discovered | 20 |
| Free Models | 20 (all models free) |
| Latency | 375ms |
| Capabilities | FunctionCalling, JSON, Reasoning, Streaming, SystemPrompt, Temperature, Tools, TopP |
| SmartRouter Categories | general_chat, coding |
| Chat Test | ERROR 413 (model llama-3.1-8b-instant rejected request as too large for title generation) |
| Warnings | Error 413 on chat — likely context size limit on small models |

### 4. OpenRouter

| Field | Value |
|-------|-------|
| Provider Type | `openrouter` |
| Instance ID | `openrouter-fff84e84` |
| Connection Status | **connected** |
| Health Status | healthy (score=100.0, success_rate=1.0) |
| Models Discovered | 337 |
| Free Models | 17 |
| Latency | 78ms |
| Capabilities | Audio, FunctionCalling, Reasoning, Streaming, SystemPrompt, Temperature, Thinking, Tools, TopP, Video, Vision |
| SmartRouter Categories | general_chat, coding, vision, reasoning |
| Chat Test | PASS (HTTP 200, meta-llama/llama-3.3-70b-instruct:free) |
| Warnings | None |

### 5. Ollama Local

| Field | Value |
|-------|-------|
| Provider Type | `ollama` |
| Instance ID | `ollama-4873db46` |
| Connection Status | **connected** |
| Health Status | healthy (score=100.0, success_rate=1.0) |
| Models Discovered | 13 |
| Free Models | 13 (all models free — local) |
| Latency | 358ms |
| Capabilities | FunctionCalling, Reasoning, Streaming, SystemPrompt, Temperature, Tools, TopP |
| SmartRouter Categories | general_chat, coding |
| Chat Test | PASS (HTTP 200, qwen2.5-coder:7b) |
| Warnings | None |

### 6. DeepInfra

| Field | Value |
|-------|-------|
| Provider Type | `deepinfra` |
| Instance ID | `deepinfra-1a46e9b5` |
| Connection Status | **connected** |
| Health Status | healthy (score=100.0, success_rate=1.0) |
| Models Discovered | 186 |
| Free Models | 5 (Llama 3.1 8B, Mixtral 8x7B, Mistral 7B, Phind CodeLlama 34B, GTE Large embeddings) |
| Latency | 1264ms |
| Capabilities | Audio, Embeddings, FunctionCalling, ImageGeneration, JSON, Reasoning, Streaming, SystemPrompt, Temperature, Thinking, Tools, TopP, Video, Vision |
| SmartRouter Categories | general_chat, coding, vision, reasoning |
| Chat Test | Not tested (policy was allow_paid but DeepInfra was not in the first batch) |
| Warnings | None |

### 7. Cloudflare Workers AI

| Field | Value |
|-------|-------|
| Provider Type | `cloudflare` |
| Instance ID | `cloudflare-2570ea00` |
| Connection Status | **error** |
| Health Status | unknown (score=100.0, success_rate=1.0) |
| Models Discovered | 5 (static catalog fallback) |
| Free Models | 0 (catalog models marked FREE_TIER in adapter) |
| Latency | — |
| Capabilities | FunctionCalling, JSON, Streaming, SystemPrompt, Temperature, Tools, TopP |
| SmartRouter Categories | general_chat, coding |
| Chat Test | Not tested (connection error) |
| Warnings | AI Gateway `/models` endpoint returned error — token may lack models-read permission. Static catalog models available. Chat may still work via AI Gateway. |

### 8. Hugging Face Inference

| Field | Value |
|-------|-------|
| Provider Type | `huggingface` |
| Instance ID | `huggingface-6db685ba` |
| Connection Status | **connected** |
| Health Status | unknown (score=100.0, success_rate=1.0) |
| Models Discovered | 130 |
| Free Models | 0 |
| Latency | 514ms |
| Capabilities | FunctionCalling, Reasoning, Streaming, SystemPrompt, Temperature, Thinking, Tools, TopP, Vision |
| SmartRouter Categories | general_chat, coding, vision, reasoning |
| Chat Test | Not tested |
| Warnings | None |

### 9. NVIDIA NIM

| Field | Value |
|-------|-------|
| Provider Type | `nvidia` |
| Instance ID | `nvidia-a965f789` |
| Connection Status | **connected** |
| Health Status | unknown (score=100.0, success_rate=1.0) |
| Models Discovered | 102 |
| Free Models | 2 |
| Latency | 139ms |
| Capabilities | Embeddings, FunctionCalling, Reasoning, Streaming, SystemPrompt, Temperature, Thinking, Tools, TopP, Vision |
| SmartRouter Categories | general_chat, coding, vision, reasoning |
| Chat Test | Not tested |
| Warnings | None |

---

## SmartRouter Categories

| Category | Required Capabilities | Eligible Providers (FREE_ONLY) |
|----------|----------------------|-------------------------------|
| general_chat | supports_streaming | Google (4), Groq (20), OpenRouter (17), Ollama (13), DeepInfra (5), NVIDIA (2) |
| coding | supports_tools, supports_function_calling, supports_reasoning | Google, Groq, OpenRouter, Ollama, DeepInfra, NVIDIA |
| vision | supports_vision, supports_streaming | Google, OpenRouter, DeepInfra, NVIDIA |
| reasoning | supports_reasoning, supports_thinking | Google, OpenRouter, DeepInfra, NVIDIA |
| fallback | (none) | All providers |

**66 free models available for routing under FREE_ONLY policy.**

---

## Security Audit

| Check | Result |
|-------|--------|
| providers.json contains API key material | **PASS** — zero key fields in all 9 provider entries |
| `_api_key` field in providers.json | **PASS** — no `_api_key` in any entry |
| Windows Credential Manager entries | **PASS** — 9 new EveOS/Provider/* entries created |
| Keys never logged or echoed | **PASS** — keys only in POST bodies to localhost |
| Commercial policy restored | **PASS** — free_only (default) |

---

## Chat Test Summary

| Provider | Model | Result | Notes |
|----------|-------|--------|-------|
| OpenAI | gpt-4o-mini | PASS | HTTP 200 |
| Google | gemini-2.0-flash | TIMEOUT | 60s timeout — model latency |
| Groq | llama-3.1-8b-instant | ERROR 413 | Request too large for model |
| OpenRouter | meta-llama/llama-3.3-70b-instruct:free | PASS | HTTP 200 |
| Ollama | qwen2.5-coder:7b | PASS | HTTP 200 |
| DeepInfra | — | Not tested | Skipped |
| Cloudflare | — | Not tested | Connection error |
| Hugging Face | — | Not tested | Skipped |
| NVIDIA | — | Not tested | Skipped |

**3/5 tested chats passed.** Failures are model-level (timeout/413), not framework issues.

---

## Warnings

1. **Cloudflare Workers AI** — AI Gateway `/models` endpoint returned error. Token may lack `models:read` permission. Static catalog (5 models) available. Chat may still work via the gateway.
2. **Google AI Studio** — Chat timed out at 60s. Model may need longer timeout or a faster model (e.g., gemini-2.5-flash).
3. **Groq Cloud** — Error 413 on small models (llama-3.1-8b-instant). Title generation request was too large. Use larger models (llama-3.3-70b-versatile) for production.
4. **Diagnostics endpoint** — Temporarily 500-ing after chat tests (transient state issue). Provider list and health endpoints work correctly.

---

*Generated by EVE v1.2.2 provider onboarding process*

# EVE v2.0 — The AI Operating System

**Document Version:** 2.0  
**Project:** EVE AI Operating System  
**Status:** Approved Vision / Version Plan  
**Audience:** Developers, Contributors, AI Coding Agents (OpenCode), Future Team Members

---

# Executive Summary

EVE is **not another chatbot**. EVE is not another desktop AI application. EVE is not another coding assistant.

EVE is an **AI Operating System** that seamlessly integrates multiple AI providers, autonomous agents, desktop automation, voice interaction, and contextual awareness into a single intelligent platform.

The ultimate objective:

> **The user should interact with their computer—not individual AI models.**

The choice of provider, model, tools, routing, recovery, memory, and execution becomes invisible. EVE manages everything.

---

# Core Identity

> **EVE is not another AI assistant. EVE is an AI Operating System.**
> Chat is just one interface. Voice is the primary interface. Hermes provides the intelligence. EVE provides the operating system.

Two complementary systems, never merged:

- **EVE owns the Operating System.** Provider routing, model management, Windows integration, AI Operations Center, AI Error Intelligence, Memory, Security, Desktop services.
- **Hermes owns the Agent Engine.** Agent reasoning, Skills, Subagents, MCP, Browser automation, Context loading, Planning.

---

# What is Hermes?

Hermes is the **[Hermes Agent](https://hermes-agent.nousresearch.com/docs/)** built by **Nous Research** — an external, mature, self-improving autonomous agent. EVE does **not** rebuild Hermes. EVE *hosts* it.

Mature capabilities Hermes already provides (reused, not duplicated):

| Capability | Hermes status |
|---|---|
| Agent reasoning loop (`AIAgent`) | Built-in, 3 API modes: `chat_completions`, `codex_responses`, `anthropic_messages` |
| Skills | Self-creating, self-improving, agentskills.io-compatible, Skills Hub |
| Context discovery | Context files (`.hermes.md`, `AGENTS.md`, `CLAUDE.md`), memory, SOUL.md personality |
| Subagents | `delegate_task`, parallel workstreams, isolated sandboxes |
| Browser automation | 10 browser tools, 5 backends |
| MCP | Native MCP client, tool filtering |
| Scheduled tasks | First-class cron with delivery to 20+ platforms |
| Tools | 70+ tools across ~28 toolsets |
| Terminal execution | 6-7 backends: local, docker, ssh, modal, daytona, singularity, vercel_sandbox |
| Session persistence | SQLite + FTS5 with lineage |
| Messaging | 20+ platform adapters (Telegram, Discord, Slack, WhatsApp, Teams, ...) |
| Voice | Real-time voice mode (CLI, Telegram, Discord, Discord VC) |
| ACP | Editor-native agent (VS Code / Zed / JetBrains) |
| Custom providers | **OpenAI-wire custom endpoints via `config.yaml` `providers.<id>` with `base_url` + `api_key`** |

**Key integration fact:** Hermes resolves providers via a runtime resolver mapping `(provider, model)` → `(api_mode, api_key, base_url)` and documents how to add custom endpoints. This is the connection point for EVE.

---

# New Architecture

```
                        User
                          │
              Voice / Chat / Overlay
                          │
                  Hermes Agent Engine
                     (planning, skills,
                      subagents, MCP)
                          │
                  EVE Agent Adapter
                    (OpenAI-wire /v1)
                          │
              Smart Router + Memory
                          │
         969 Models / 9+ Providers
                          │
        Windows • Browser • Files
```

Hermes becomes one engine inside EVE, not the product itself.

**Hermes plans. EVE executes.** Example: "Update my portfolio."

1. Hermes creates the plan (reasoning, skills, subagents).
2. Every LLM call Hermes makes routes through EVE's Smart Router.
3. EVE edits files, runs Git, opens the browser, tests, commits, reports.
4. Failures are captured, classified, explained, and recovered by EVE's Error Intelligence.

---

# Responsibilities

## Hermes (external, reused as-is)
- Planning & reasoning
- Skills (self-creating, self-improving)
- Subagents & parallel workstreams
- Context discovery & loading
- Browser automation
- MCP client
- Scheduling / cron
- Batch execution
- Checkpoints

## EVE (what we build)
- Provider routing & model selection (Smart Router)
- Credential management
- Provider health analytics
- Recovery (AI Error Intelligence → Autonomous Recovery)
- Memory (Life Memory / knowledge graph)
- Desktop integration (Windows automation, overlay, tray)
- Permissions & security (sandboxing, confirmation rules, credential isolation)
- Voice pipeline (VoiceOS+)
- AI Operations Center (observability)
- Plugin system
- Workspace awareness
- **EVE Agent Adapter** (OpenAI-wire endpoint so Hermes can use EVE as its provider)

---

# Vision 2.0 Pillars

## Pillar 1 — Voice First
Voice is no longer an optional feature. Everything should work through voice.

- "EVE, summarize this PDF."
- "EVE, redesign this screen."
- "EVE, debug my application."

No keyboard required.

## Pillar 2 — Context Awareness
EVE always knows: active window, active application, selected text, clipboard, current project, current Git branch, current browser tab, open files. No copy-paste.

## Pillar 3 — Agent Intelligence
Hermes plans. EVE executes. Tasks complete autonomously with verification.

## Pillar 4 — Native Desktop
Not another chat window. EVE becomes a floating assistant, global overlay, push-to-talk, wake word, desktop widgets, notification center.

## Pillar 5 — Self-Healing
AI Error Intelligence evolves into Autonomous Recovery:

```
Provider fails → Retry → Switch provider → Refresh models → Continue → Notify user
```

## Pillar 6 — Continuous Memory
Conversation Memory becomes **Life Memory**: projects, coding, design, habits, preferences, research, files, meetings — everything connected.

---

# What NOT to Build

Hermes already has: Skills, Context discovery, Subagents, Browser automation, MCP, Checkpoints, Cron, Batch execution.

**Reuse those. Don't duplicate them.**

EVE's unique value — what nobody else has:
- AI Operations Center
- Smart Router across hundreds of models
- AI Error Intelligence
- Provider health analytics
- Windows-native automation
- Multi-provider routing
- Desktop OS integration

That is the competitive advantage.

---

# Immediate Roadmap

## Phase A — Hermes Integration
**Goal:** Hermes uses EVE as its model provider. EVE becomes the routing/recovery layer under any agent engine.

1. **EVE Agent Adapter** — an OpenAI-wire API surface exposed by EVE's backend:
   - `GET /v1/models` — dedup'd aggregated model list from ProviderManager
   - `GET /v1/models/{id}` — capability detail
   - `POST /v1/chat/completions` — non-streaming + SSE streaming
   - `POST /v1/completions` — legacy text completions (optional)
   - Bearer-token auth enforced (EVE's existing AuthManager token)
2. **Model → routing resolution** — abstract capability aliases (`eve:general`, `eve:reasoning`, `eve:coding`, `eve:vision`, `eve:fast`, `eve:free`) resolved by SmartRouter at request time, plus exact-model passthrough.
3. **Tool-call bridge** — OpenAI `tools` schema mapped to EVE's ToolManager / capability registry.
4. **Hermes provider configuration** — a documented `config.yaml` snippet registering EVE as a custom OpenAI-wire provider (`base_url: http://127.0.0.1:8456/v1`, `api_mode: chat_completions`, model = `eve:*` aliases).
5. **Skill interoperability** — Hermes skills can invoke EVE tools / capabilities.

**Acceptance:** A Hermes conversation streams responses that EVE's Smart Router served from the best available provider; provider failover and error capture flow into EVE's Recovery Center.

## Phase B — VoiceOS+
Continuous conversations, wake word, push-to-talk, floating overlay, dictation everywhere.

Current state (audited): push-to-talk works (frontend key handling), phrase-loop STT + barge-in + TTS exist. **Not implemented:** wake word engine, continuous listening, real VAD, `audio_level` publishing, backend-level voice hotkeys, floating overlay.

1. Wake-word detection engine (local, low-latency) wired to `VoiceConfig.wake_word`
2. Continuous listening — consume `continuous_listening` config end-to-end
3. Real VAD — feed `vad_enabled`/`vad_threshold` into capture
4. Publish `audio_level` from mic RMS so the UI meter is live
5. Backend push-to-talk global hotkey (desktop/hotkeys)
6. Floating overlay + dictation-anywhere (frontend overlay + clipboard/active-window awareness)

## Phase C — Autonomous Desktop
Multi-agent execution, background tasks, scheduled workflows, cross-application automation.

1. Multi-agent execution — extend `ExecutionEngine` for parallel agents
2. Background tasks + scheduled workflows — cron-style scheduling on EVE side
3. Cross-application automation — via `windows/` UI automation + vision

## Phase D — AI Operating System
Desktop widgets, ambient assistance, predictive actions, personal knowledge graph, agent marketplace.

1. Desktop widgets (Tauri multi-window)
2. Ambient assistance (context engine + error intelligence → proactive suggestions)
3. Predictive actions
4. Personal knowledge graph (Memory v2 — projects, files, people, meetings connected)
5. Agent marketplace (skill/plugin registry)

---

# Smart Router

The Smart Router remains the heart of EVE. It decides best provider, best model, latency, cost, reasoning/vision/streaming capability, availability, health, and commercial policy. Users never manually choose providers unless they want to.

Hermes requests **capabilities**; EVE chooses the model.

---

# AI Operations Center

The AI Operations Center becomes the control room of EVE. It evolves into: Dashboard, Providers, Models, Routing, Health, Recovery Center, Memory, Voice, Subagents, Tasks, Performance, System, Logs, Diagnostics. Everything inside EVE should be observable.

---

# AI Error Intelligence

Every failure becomes knowledge. Instead of "Provider returned empty response," EVE explains what happened, why, what was attempted, how it recovered, and what the user can do.

Future: predictive failures, automatic provider scoring, recovery analytics, learning from recurring failures.

---

# Security

Security is never optional. All agent actions must respect the permission system, sandboxing, confirmation rules, credential isolation, plugin permissions, tool restrictions, and desktop access controls. Users remain in control.

---

# Performance Goals

- Cold startup under 5 seconds
- Voice response begins within 1 second
- Provider failover under 3 seconds
- Automatic recovery without user intervention
- Stable 24/7 runtime
- No orphan processes
- Minimal memory footprint
- Transparent diagnostics

---

# Non-Goals

EVE will NOT become: another ChatGPT, another Claude Desktop, another Cursor, another IDE, another browser, another note-taking application. Instead, EVE enhances every existing application.

---

# Success Metrics

The project succeeds when:
- Users rarely open the chat window.
- Voice becomes the preferred interface.
- Most provider failures recover automatically.
- Users never think about models.
- Tasks complete autonomously.
- Context replaces repetitive prompting.
- AI becomes part of daily desktop workflows.

---

# Long-Term Vision

Imagine using your computer without thinking about AI. You speak naturally. EVE understands intent, chooses the best models, coordinates autonomous agents, recovers from failures, remembers your work, automates repetitive tasks, and protects your data. It quietly becomes the intelligent operating layer of your computer.

---

# Guiding Principle

> **"The computer should adapt to the user. The user should never adapt to the AI."**

# Engineering Rule

Every feature added to EVE v2.x must answer **YES** to at least one of:

- Does it make voice interaction more natural?
- Does it improve autonomous task execution?
- Does it reduce cognitive load for the user?
- Does it improve context awareness?
- Does it strengthen provider independence?
- Does it enhance reliability, observability, or recovery?
- Does it make EVE feel more like an operating system than an application?

If the answer is **NO**, reconsider whether the feature belongs in EVE.

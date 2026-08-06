# HERMES-DEV SETUP REPORT

Date: 2026-08-06
Created: independent Hermes profile `hermes-dev` acting as an **AI Software Engineer**.
The existing Hermes installation used by EVE, the default profile, all EVE configuration, and the global `HERMES_HOME` were **not modified**.

---

## 1. Profile Location

| Item | Value |
|------|-------|
| Profile name | `hermes-dev` |
| Profile directory (HERMES_HOME) | `C:\Users\swara\AppData\Local\hermes\profiles\hermes-dev` |
| Created via | `hermes profile create hermes-dev --no-alias` (native profiles; **not cloned** — no EVE settings inherited) |
| Bundled skills | 71 synced at creation |
| Executable | `C:\Users\swara\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe` (shared binary; data fully isolated) |

## 2. Configuration Path

| File | Purpose |
|------|---------|
| `...\profiles\hermes-dev\config.yaml` | Profile config (model, fallback chain, toolsets, workspace, persona, security) — written fresh |
| `...\profiles\hermes-dev\.env` | Per-profile secrets (free-provider API keys only; no EVE endpoint) |
| `...\profiles\hermes-dev\SOUL.md` | Hermes Developer system prompt (debugging specialist persona) |
| `...\profiles\hermes-dev\workspace\`, `sessions\`, `memories\`, `logs\`, `skills\`, `cron\` | Isolated per-profile state |

`config.yaml` validates clean: `load_config()` OK, `validate_config_structure()` → **0 issues**.

## 3. Active Providers

**Primary:** Google Gemini Free — `gemini-2.5-flash` (verified responding).

**Automatic failover chain** (`fallback_providers`, tried in order on rate-limit 429 / overload 529 / 503 / connection failure):

| # | Provider | Model | Status |
|---|----------|-------|--------|
| 1 | Google Gemini (gemini) | `gemini-2.5-flash` | ✅ key OK, live test passed |
| 2 | Groq Free | `llama-3.3-70b-versatile` | ✅ key OK |
| 3 | HuggingFace Inference | `Qwen/Qwen2.5-7B-Instruct` | ✅ key OK |
| 4 | Cloudflare Workers AI | `@cf/zai-org/glm-4.7-flash` | ✅ key OK |
| 5 | Z.AI GLM Flash | `glm-4.7-flash` | ⚠️ no key set (placeholder; inactive unless `ZAI_API_KEY` added) |
| 6 | Ollama (optional, local) | `llama3.2` | ⚠️ not running (skipped; local-only, no key needed) |

- **No EVE dependency**: base_url is never `127.0.0.1:8456`. No `EVE_API_KEY` in `.env`. Verified no EVE tokens/URLs present.
- Provider credentials are per-profile (`.env` overrides shell env) — the global/default Hermes environment is untouched.

## 4. Enabled Tools

`toolsets` in config.yaml:

- `hermes-cli`, `browser`, `code_execution`, `coding`, `debugging`, `file`, `terminal`, `web`, `search`, `memory`, `git`, `mcp`, `vision`, `context_engine`, `todo`, `skills`

Covers: filesystem, git, terminal/shell (PowerShell/batch via `terminal.backend: local`), browser automation, HTTP/web, search, directory indexing, MCP, log reading, code execution, debugging, vision.

## 5. Workspace

- Primary workspace: `E:\Eve_Ai` (set as `terminal.cwd` and `agent.cwd`).
- Verified: `E:\Eve_Ai` exists, is a git work tree (`rev-parse --is-inside-work-tree` = true), latest commit readable.

## 6. Startup Command

```
hermes -p hermes-dev                     # interactive dev session (default model gemini-2.5-flash)
hermes -p hermes-dev -z "prompt"         # one-shot
hermes -p hermes-dev chat                # explicit chat
hermes -p hermes-dev gateway start       # persistent gateway under this profile
hermes -p hermes-dev doctor              # diagnostics
```

Wrapper alias `hermes-dev` was **not** created (`--no-alias`) to keep PATH clean; always invoke with `-p hermes-dev` (per-process, never touches global HERMES_HOME).

## 7. Verification Results

| Check | Result |
|-------|--------|
| ✓ Default Hermes profile unchanged | PASS — `profile list` shows `◆default  eve:general` (Custom endpoint / EVE), unchanged |
| ✓ EVE profile unchanged | PASS — default config still `base_url: http://127.0.0.1:8456/v1`, `default: eve:general` |
| ✓ hermes-dev created | PASS — `profile list` shows `hermes-dev  gemini-2.5-flash` |
| ✓ Workspace accessible | PASS — `E:\Eve_Ai` exists, writable, is git root |
| ✓ Git accessible | PASS — `git log` works |
| ✓ Terminal works | PASS — `terminal.backend: local`, cwd `E:\Eve_Ai` |
| ✓ Browser automation available | PASS — `browser` toolset enabled |
| ✓ Model responds | PASS — `hermes -p hermes-dev -z "Reply with exactly: HERMES_DEV_OK"` → `HERMES_DEV_OK` (via Gemini free) |
| ✓ No dependency on EVE | PASS — no EVE endpoint/key anywhere in profile; providers call Gemini/Groq/HF/Cloudflare directly |

## 8. Isolation Verification

- Global `HERMES_HOME` (user + machine): **unchanged** = `C:\Users\swara\AppData\Local\hermes`.
- Default profile files (`...\hermes\config.yaml`, `.env`, `SOUL.md`): **untouched** (still EVE-pointing).
- EVE config (`~/.eve/*`, `E:\Eve_Ai\config\*`): **untouched** — read-only inspection only.
- No files modified inside `C:\Users\swara\AppData\Local\hermes` outside the new `profiles\hermes-dev\` directory.
- hermes-dev is a fully independent `HERMES_HOME` (own config, `.env`, memory, sessions, skills, logs). Switching profiles is per-process (`-p hermes-dev`); nothing sticky was changed.
- `.env` secrets live only in the profile dir (outside the `E:\Eve_Ai` git repo) — no credential exposure.

## 9. Limitations

- **Z.AI GLM Flash** is configured but has no API key — will only activate if `ZAI_API_KEY` is added to `...\profiles\hermes-dev\.env`.
- **Ollama** entry is present but Ollama is not currently running; it activates automatically when a local Ollama server is up (`http://127.0.0.1:11434/v1`).
- **Cloudflare Workers AI** is functional but can be rate-limited / return 410/429 on the free tier; it is positioned 4th in the chain for this reason.
- **Primary auth failure** vs. mid-stream failure: Hermes failover triggers on 429/529/503/connection errors and on primary auth failure at startup; a mid-request silent failure falls through the chain per Hermes' native behavior.
- Shared venv/binary with the default install (Hermes' profile model is data-level isolation; binary isolation would require a separate install — see HERMES_INSTALLATION_AUDIT.md).
- `git` toolset is enabled via the registry; the exact tool name surfaced depends on Hermes' tool manifest for the running binary version (v0.20.0).

---

*Created without modifying the existing Hermes installation, the default profile, EVE configuration, or the global HERMES_HOME.*

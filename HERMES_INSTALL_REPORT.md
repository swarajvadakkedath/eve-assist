# HERMES INSTALLATION REPORT

## Installation Summary

| Item | Value |
|------|-------|
| **Hermes Version** | v0.20.0 (2026.8.3) |
| **Install Method** | Official PowerShell installer (`install.ps1`) |
| **Install Path** | `C:\Users\swara\AppData\Local\hermes\hermes-agent` |
| **Config Dir** | `C:\Users\swara\AppData\Local\hermes\` |
| **Python** | 3.12.10 (managed by uv) |
| **OpenAI SDK** | 2.24.0 |
| **Platform** | Windows (native) |

## Verification

| Check | Status |
|-------|--------|
| CLI launches | ✅ `hermes --version` returns v0.20.0 |
| Doctor diagnostics | ✅ All required packages present |
| Virtual environment | ✅ Python 3.12.10 venv active |
| Config files | ✅ config.yaml + .env present |
| Skills synced | ✅ 71 bundled skills synced |
| PATH configured | ✅ `hermes` command accessible |

## Dependencies Installed

Core packages (100 total):
- hermes-agent 0.20.0
- openai 2.24.0
- fastapi 0.133.1
- pydantic 2.13.4
- httpx 0.28.1
- rich 14.3.3
- pyyaml 6.0.3
- python-dotenv 1.2.2
- mcp 1.28.1
- pywin32 311
- And 90+ more

## Warnings

| Warning | Impact |
|---------|--------|
| SQLite 3.49.1 (WAL-reset bug) | Minor — fixed in 3.51.3+ |
| Config version outdated (v0→33) | Fixed by adding `version: 33` to config.yaml |
| Browser tools npm install failed | Non-critical — browser tools require manual `npm install` |
| TUI npm install failed | Non-critical — TUI requires manual `npm install` in `ui-tui/` |

## Files Modified

- `~/.hermes/config.yaml` — Added `version: 33` header, configured EVE endpoint
- `~/.hermes/.env` — Added `EVE_API_KEY` for EVE authentication

## Configuration

```yaml
model:
  default: "eve:general"
  provider: "custom"
  api_key: "${EVE_API_KEY}"
  base_url: "http://127.0.0.1:8456/v1"
```

```bash
# .env
EVE_API_KEY=eve-dev-token-xK9mP2qR7vN4wL8j
```

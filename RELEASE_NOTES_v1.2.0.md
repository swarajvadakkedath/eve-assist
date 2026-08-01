# EVE v1.2.0 Release Notes

**Release date:** 2026-07-31
**Version:** 1.2.0
**Installer:** `Eve_1.2.0_x64-setup.exe` (130.4 MB)
**SHA-256:** `999BAADDE4D8D80B2F10B12D02149236064D06AEE3FA3207322744FCCD8CB1AC`

---

## Highlights

### Agent Core
- Full agent tool execution through Planner → Capability → Permission pipeline
- Context-aware planning with workspace intelligence integration
- Streaming response support for real-time output

### Workspace Intelligence
- Automatic workspace detection (Git, project structure, active window)
- Git-grounded context with branch, status, and diff awareness
- Workspace cache and invalidation for responsive context switching

### Memory
- Scoped persistent memory with graph-based storage
- Injection boundary enforcement — memory treated as untrusted context
- Memory store, search, recall, and forget operations
- Restart-persistent memory across backend restarts

### Vision/OCR
- Bundled Tesseract OCR — no system installation required
- Screen capture and OCR pipeline
- Vision observations treated as untrusted context

### Routing/Providers
- Multi-provider support: Google AI Studio, Groq, OpenAI, Anthropic, Ollama, OpenRouter
- Smart routing with category-based provider selection (general, coding, vision, reasoning)
- Quota-aware failover between providers
- Per-conversation provider/model switching

### Conversation Persistence
- Conversations persist across backend and application restarts
- File-based repository with in-memory index loaded at startup
- Multi-restart survival verified (50+ conversations)

### Security
- No plaintext API keys in logs or configuration
- Credential redaction in all output paths
- Permission enforcement on tool execution
- Plugin sandbox isolation

### Desktop/Packaging
- Tauri-based desktop application with system tray
- Bundled Python 3.12.9 runtime (no system Python required)
- NSIS installer with proper uninstall cleanup
- User data (`~/.eve`) preserved across reinstalls

---

## Known Limitations

- **Physical Voice (microphone → STT → assistant → TTS → speaker):** UNPROVEN — HARDWARE. No suitable hardware acceptance was completed. Voice subsystem initializes but end-to-end physical voice workflow not validated.
- **Provider availability:** Depends on external API quotas and rate limits. Not an EVE product defect.
- **Bundled OCR:** Accepts bundled Tesseract. System Tesseract not required and not used.

---

## Installation

1. Download `Eve_1.2.0_x64-setup.exe`
2. Verify SHA-256: `999BAADDE4D8D80B2F10B12D02149236064D06AEE3FA3207322744FCCD8CB1AC`
3. Run installer (silent: `/S` flag available)
4. User data stored at `~/.eve` — preserved across reinstalls

---

## Regression

- 364/364 backend tests PASS
- Post-promotion regression: 364/364 PASS
- Frontend production build: clean (Vite, 135 modules)

---

*Built from commit `7279244` on branch `v1.2.0/agent-core`*
*Toolchain: Python 3.12.9 (bundled), Node 24.18.0, Rust 1.95.0*

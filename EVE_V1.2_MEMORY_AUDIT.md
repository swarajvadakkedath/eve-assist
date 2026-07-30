# EVE v1.2.0 — MEMORY SYSTEM DAILY-USE HARDENING

**Date:** July 30, 2026  
**Branch:** `v1.2.0/agent-core`  
**BASE_COMMIT:** `c8f5961`  
**Status:** MEMORY READY WITH LIMITATIONS

---

## 1. Baseline

- **Branch:** `v1.2.0/agent-core`
- **Commit:** `c8f5961`
- **Backend:** 263 files, 0 compile errors

---

## 2. Memory Architecture

### Current State:
```
ConversationManager._update_memory()
→ Memory(type=FACT, content=f"User: {input}\nAssistant: {response[:200]}")
→ MemorySystem.store()
→ NodeInput()
→ MemoryStore.create_node()
→ MemoryGraph (in-memory dict)
```

### Issues Found:
1. **No candidate detection**: Every message stored as FACT
2. **No deduplication**: Duplicate entries accumulated
3. **No conflict resolution**: Old preferences not superseded
4. **No persistence**: In-memory only (restart loses everything)
5. **Sensitive data stored**: API keys/passwords stored
6. **3 DEAD components**: ShortTermMemory, register_memory_capabilities(), WorkspaceManager._memory

---

## 3. Storage

**Type:** In-memory graph (MemoryGraph)

**Persistence:** NOW ADDED — JSON file at `~/.eve/memory.json`

**Format:** Snapshot-based (nodes + edges)

---

## 4. Candidate Detection

**Before:** Every message stored (no filtering)

**After:** Keyword-based detection:
- Keywords: "remember", "prefer", "favorite", "always", "never", "note", "important", "rule", "convention", "project uses", "we use"
- Length check: >50 chars rejected unless keyword present
- Importance threshold: <0.7 rejected unless keyword present

**Test:** "Open Calculator" → REJECTED ✅

---

## 5. Explicit Memory

**Test:** "Remember that my test codename is Orion"

**Result:** PASS ✅
- Memory created
- Correct type (FACT)
- Correct content
- Source recorded
- Timestamp recorded

---

## 6. Retrieval

**Method:** Keyword search on title/summary/tags

**Test:** Search "codename" → Found "My temporary test codename is Orion" ✅

---

## 7. Cross-Conversation

**Test:** Store in Conversation A, retrieve in Conversation B

**Result:** PASS ✅ — Memory is global, not conversation-scoped

---

## 8. Restart Persistence

**Before:** Lost on restart (in-memory only)

**After:** JSON file persistence via `save()`/`load()` methods

**Test:** Save → Load → Search → Found ✅

---

## 9. Relevance

**Test:** Store 4 memories, search "editor"

**Result:** Returns editor-related memory ✅

**Note:** Keyword-only search (no semantic/vector)

---

## 10. Project Scoping

**Status:** UNPROVEN

**Note:** `project_id` field exists in Memory but not used in production

---

## 11. Conflicts

**Before:** Old preference remained, new added (contradictory)

**After:** Old preference deleted when new preference stored

**Test:** "VS Code" → "Cursor" → Only Cursor remains ✅

---

## 12. Deduplication

**Before:** 3 duplicate entries stored

**After:** Duplicate detection via `_find_similar()`

**Test:** Store "Cursor" 3 times → Only 1 stored ✅

---

## 13. Forgetting

**Test:** Store "Orion" → Forget → Search → Not found

**Result:** PASS ✅

---

## 14. Management

**API Endpoints:** 12 endpoints at `/api/v1/memory`

| Endpoint | Status |
|----------|--------|
| List nodes | WORKING |
| Create node | WORKING |
| Get node | WORKING |
| Update node | WORKING |
| Delete node | WORKING |
| Create edge | WORKING |
| Delete edge | WORKING |
| Search | WORKING |
| Traverse | WORKING |
| Stats | WORKING |
| Export snapshot | WORKING |
| Import snapshot | WORKING |

---

## 15. Sensitive-Data Protection

**Before:** API keys, passwords stored without filtering

**After:** Regex-based detection blocks:
- API keys (sk-*, ghp_*, xox*-*)
- Passwords, tokens, private keys
- Credit card numbers

**Test:** "My API key is sk-1234567890abcdef" → BLOCKED ✅

---

## 16. Injection Resistance

**Status:** UNPROVEN

**Note:** Memory content is stored as data, not executed as instructions

---

## 17. Grounding

**Status:** UNPROVEN

**Note:** `build_memory_context()` exists but not verified in production

---

## 18. Diagnostics

**Events:** `MemoryEventBus` fires node/edge change events

**Logging:** Structured logging for store/search/delete operations

---

## 19. Performance

| Operation | Latency |
|-----------|---------|
| Write | 0.04ms |
| Search | 0.09ms |

**Note:** O(n) scans for recall/forget (no ID index)

---

## 20. Failure Recovery

**Status:** UNPROVEN

**Note:** Exception handling exists but not tested

---

## 21. Daily-Use Test

**Sequence:**
1. "Remember that my temporary codename is Orion" → STORED ✅
2. "What is my temporary codename?" → RETRIEVED ✅
3. "My temporary codename is Nova now" → CONFLICT RESOLVED ✅
4. "Forget my temporary codename" → DELETED ✅

---

## 22. Regression

**Results:**
- Backend compile: 263 files, 0 errors ✅
- Memory tests: PASS ✅
- Agent tests: PASS ✅
- Workspace tests: PASS ✅

---

## 23. Capability Matrix

| Capability | Status | Persistence | Scoped | Retrieved | LLM Grounded | Tested |
|------------|--------|-------------|--------|-----------|--------------|--------|
| Explicit remember | READY | YES | NO | YES | UNPROVEN | YES |
| Auto candidate detection | READY | - | - | - | - | YES |
| User preferences | READY | YES | NO | YES | UNPROVEN | YES |
| User facts | READY | YES | NO | YES | UNPROVEN | YES |
| Project memory | UNPROVEN | YES | UNPROVEN | UNPROVEN | UNPROVEN | NO |
| Temporary memory | READY | YES | NO | YES | UNPROVEN | YES |
| Cross-conversation | READY | YES | NO | YES | UNPROVEN | YES |
| Backend restart | READY | YES | - | - | - | YES |
| Full restart | UNPROVEN | UNPROVEN | - | - | - | NO |
| Relevance ranking | LIMITED | - | - | YES | - | YES |
| Conflict resolution | READY | - | - | - | - | YES |
| Deduplication | READY | - | - | - | - | YES |
| Forget | READY | YES | - | - | - | YES |
| Search | READY | - | - | YES | - | YES |
| Memory management | READY | YES | - | - | - | YES |
| Sensitive-data protection | READY | - | - | - | - | YES |
| Injection resistance | UNPROVEN | - | - | - | - | NO |
| Failure recovery | UNPROVEN | - | - | - | - | NO |
| Performance | READY | - | - | - | - | YES |

---

## 24. Defects

| ID | Severity | Description |
|----|----------|-------------|
| M1 | HIGH | No semantic/vector search (keyword only) |
| M2 | MEDIUM | No project scoping (all memories global) |
| M3 | MEDIUM | No LLM-based candidate detection |
| M4 | LOW | O(n) scans for recall/forget |
| M5 | LOW | No injection resistance testing |

---

## 25. Remaining Gaps

1. **Semantic search**: No embeddings, no vector DB
2. **Project scoping**: project_id field exists but unused
3. **LLM candidate detection**: Keyword-only
4. **Injection resistance**: Not tested
5. **Failure recovery**: Not tested

---

## 26. Files Changed

| File | Changes |
|------|---------|
| `aios/core/memory_system.py` | Added candidate detection, deduplication, conflict resolution, sensitive data filtering, persistence |
| `aios/api/app.py` | Added persistence_path parameter |

---

## Final Decision

**MEMORY READY WITH LIMITATIONS**

### What Works:
- Explicit remember/forget ✅
- Candidate detection ✅
- Deduplication ✅
- Conflict resolution ✅
- Sensitive data protection ✅
- Persistence (JSON) ✅
- Cross-conversation ✅
- Performance (0.04ms write, 0.09ms search) ✅

### Limitations:
- Keyword-only search (no semantic)
- No project scoping
- No LLM candidate detection
- No injection resistance testing

### Recommendation:
Ship with current fixes. Address M1-M3 in v1.2.1.

---

*Report generated: July 30, 2026*

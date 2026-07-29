# 10 — Future Roadmap

> **Status:** Approved · v2.0.0  
> **Scope:** Product roadmap and capability forecast beyond AIOS v1.0  
> **Last Updated:** 2026-07-21  
> **Current Release:** v1.0.0  
> **Maintainer:** Product Manager

---

## Table of Contents

1. [Roadmap Philosophy](#1-roadmap-philosophy)
2. [Timeline Overview](#2-timeline-overview)
3. [Version 1.1 — Foundation Extensions](#3-version-11--foundation-extensions)
4. [Version 1.5 — Connected Intelligence](#4-version-15--connected-intelligence)
5. [Version 2.0 — Autonomous Platform](#5-version-20--autonomous-platform)
6. [Version 3.0 — Distributed Ecosystem](#6-version-30--distributed-ecosystem)
7. [Research & Experimental](#7-research--experimental)
8. [Deferred](#8-deferred)
9. [Dependency Map](#9-dependency-map)
10. [Appendix A — Capability Maturity Model](#10-appendix-a--capability-maturity-model)
11. [Appendix B — Risk Registry](#11-appendix-b--risk-registry)

---

## 1. Roadmap Philosophy

### 1.1 Guiding Principles

1. **Every feature must justify its existence against the Vision.** If it doesn't make Eve a better co-pilot, it doesn't ship. No feature creep.

2. **Local-first is non-negotiable.** Cloud features are opt-in, never required. The core product works fully offline forever.

3. **Infrastructure before features.** A feature built on shaky foundations creates more debt than value. Each version solidifies the layer below before building the layer above.

4. **Research tracks are not commitments.** Items in Research may be deferred indefinitely, pivoted, or cancelled based on findings. No roadmap item is a promise.

5. **Complexity compounds. Every dependency added now limits optionality later.**

### 1.2 Roadmap Categories

| Category | Meaning | Likelihood |
|----------|---------|------------|
| **Short Term** | Next 1-3 months. Directly builds on existing infrastructure. | > 90% |
| **Medium Term** | 3-9 months. Requires moderate new infrastructure. | > 60% |
| **Long Term** | 9-24 months. Major new capability or platform expansion. | > 30% |
| **Research** | No active development. Feasibility study in progress. | < 20% |
| **Experimental** | Prototype exists or planned. May not ship. | < 40% |
| **Deferred** | Viable concept but deliberately postponed. | 0% (for now) |

### 1.3 How to Read This Document

Each roadmap item follows a consistent structure:

```
Vision        — What the user experiences when this ships
Motivation    — Why this matters, what problem it solves
Dependencies  — What must exist first (infrastructure, data, ecosystem)
Complexity    — [Low | Medium | High | Very High]
Priority      — [P0 | P1 | P2 | P3]
Milestone     — Version + estimated quarter
Risks         — What could block or delay this item
Success       — Measurable criteria for calling this done
```

---

## 2. Timeline Overview

```
                   2026                            2027                            2028
     Q3           Q4           Q1           Q2           Q3           Q4           Q1+
─────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┼──────────
     │                                                                              
     │  v1.0                                                                        
     │  ┌────────────────────────────────────────────────────────────────────
     │  │ Foundation Complete                                                      
     │  └────────────────────────────────────────────────────────────────────
     │                                                                              
     │       v1.1                                                                   
     │       ┌───────────────────────────────────────────────────────
     │       │ Foundation Extensions                                                 
     │       │ • Plugin Marketplace       • Semantic Search                         
     │       │ • Knowledge Graph          • Self Learning (basic)                   
     │       │ • Linux Support (beta)     • Personal Knowledge Graph                
     │       └───────────────────────────────────────────────────────
     │                                                                              
     │                 v1.5                                                         
     │                 ┌─────────────────────────────────────────────────
     │                 │ Connected Intelligence                                     
     │                 │ • Cloud Sync (opt-in)   • Multi-Device                       
     │                 │ • RAG Pipeline          • Knowledge Graph Reasoning          
     │                 │ • API Server            • macOS Support                      
     │                 │ • Self Learning (advanced)                                  
     │                 └─────────────────────────────────────────────────
     │                                                                              
     │                                   v2.0                                       
     │                                   ┌────────────────────────────────
     │                                   │ Autonomous Platform                     
     │                                   │ • AI Agents           • Team Collaboration
     │                                   │ • Shared Memory       • Enterprise Suite  
     │                                   │ • Workflow Marketplace                    
     │                                   └────────────────────────────────
     │                                                                              
     │                                                          v3.0                
     │                                                          ┌─────────
     │                                                          │ Distributed       
     │                                                          │ • Distributed Agents
     │                                                          │ • Remote Execution  
     │                                                          └─────────
```

---

## 3. Version 1.1 — Foundation Extensions

**Target:** 3 months post-v1.0 (Q4 2026)  
**Theme:** Strengthen the core. Extend what exists. Enable the ecosystem.  
**Risk Level:** Low — primarily builds on existing infrastructure.

---

### 3.1 Plugin Marketplace

**Category:** Short Term  
**Vision:** Users browse, install, and update plugins from a curated marketplace within the Eve UI. One-click install. Automatic updates. Community ratings.

**Motivation:** The Plugin SDK (ADR-0001, 13-Plugin-SDK.md) provides the technical foundation, but there is no distribution channel. A marketplace transforms plugins from a developer-only feature to a user-facing ecosystem. This is the single highest-leverage investment for platform growth.

**Dependencies:**
- Plugin SDK complete and stable (v1.0)
- Plugin manifest format finalized (`plugin.yaml`)
- Plugin isolator and sandbox verified

**Complexity:** Medium  
**Priority:** P1

**Estimated Milestone:** v1.1, Q4 2026

**Risks:**
- **Moderation:** Malicious plugins on the marketplace damage trust. Automated validation + manual review pipeline required.
- **Version fragmentation:** Plugins target different SDK versions. Backward compatibility policy needed.
- **Hosting cost:** Marketplace backend requires a server. Must be optional — local/offline plugin install remains supported.

**Success Criteria:**
- 10+ community plugins published within 1 month of launch
- Plugin install/uninstall/update flow tested and documented
- Plugin sandbox verified to prevent host system access
- Plugin manifest validation catches 100% of malformed manifests

---

### 3.2 Semantic Search

**Category:** Short Term  
**Vision:** Users search conversations, tools, settings, and plugins with natural language queries. Results are ranked by relevance, returned in under 500ms, and include context snippets.

**Motivation:** The current search is keyword-based (`SequenceMatcher` fuzzy matching in the Capability Registry, basic SQL LIKE queries in the database). As the knowledge base grows (conversations, memory entries, tool outputs), users need to find information by meaning, not exact words. The vector extension (`sqlite-vec`) is already in the stack (ADR-0006) but not wired into the UI.

**Dependencies:**
- SQLite with vector extension (ADR-0006 — implemented)
- Embedding model integration (existing AI Router — ADR-0003)
- Storage adapter for vector index (referenced in ADR-0007)

**Complexity:** Medium  
**Priority:** P1

**Estimated Milestone:** v1.1, Q4 2026

**Risks:**
- **Embedding quality:** Open-source embedding models vary significantly. Model selection requires benchmarking.
- **Index size:** Vector index grows linearly with content. 100k entries at 1536 dimensions = ~600MB. Pruning strategy needed.
- **Latency:** Embedding generation for new content adds ~200-500ms per write. Async indexing required.

**Success Criteria:**
- Search latency < 500ms for 50k indexed entries (P50)
- Recall@10 > 0.85 on a curated test set of 100 queries
- Users report finding what they need in 2 searches or fewer

---

### 3.3 Personal Knowledge Graph (MVP)

**Category:** Short Term  
**Vision:** Eve automatically builds a personal knowledge graph from conversations, tools executed, and files accessed. Users see entities (projects, people, tools, files) and their relationships. Knowledge persists across sessions and grows over time.

**Motivation:** The Memory Architecture (ADR-0007) defines the vision of a temporal knowledge graph with 4 super types and 12+ edge types. The Memory Core (ADR-0008) implements the zero-dependency graph subsystem. What's missing is the automatic population pipeline — taking raw conversation and tool data and extracting structured knowledge.

**Dependencies:**
- Memory Core (ADR-0008 — implemented)
- Memory Architecture design (ADR-0007 — approved)
- AI Router for entity extraction (ADR-0003 — implemented)
- Storage adapter layer for persistence (ADR-0007 — not yet implemented)

**Complexity:** High  
**Priority:** P1

**Estimated Milestone:** v1.1–v1.5, Q4 2026–Q1 2027

**Risks:**
- **Extraction quality:** LLM-based entity extraction is imperfect. False positives pollute the graph. Confidence thresholds are critical.
- **Graph size:** Unbounded growth. Importance decay and archival strategy must be implemented before shipping to users.
- **User understanding:** Users need a clear mental model of "what Eve remembers." A knowledge graph is abstract — the UI must make it concrete.

**Success Criteria:**
- Knowledge graph automatically populated from 100 conversation turns with > 80% precision on entity extraction
- Graph queries return results in < 500ms for 10k nodes
- Users can browse their knowledge graph in the Memory Workspace

---

### 3.4 Self Learning (Basic)

**Category:** Short Term — Experimental  
**Vision:** Eve learns from user corrections. If a user corrects a tool result, changes a setting, or rephrases a command, Eve adapts future behaviour without explicit configuration.

**Motivation:** One of the highest-requested features for AI assistants is "it should learn from its mistakes." Currently, Eve has no feedback loop. Every mistake is repeated until the user configures a workaround. Basic self-learning closes the loop for the most common failure patterns: wrong tool selection, incorrect parameters, overly verbose responses.

**Dependencies:**
- Memory System (v1.0 — implemented)
- Usage analytics infrastructure (must be built — local-only, opt-in)
- User feedback mechanism (UI for "thumbs up/down" on tool results)

**Complexity:** High  
**Priority:** P2

**Estimated Milestone:** v1.1 (experimental), Q4 2026

**Risks:**
- **Feedback sparsity:** Most users won't provide explicit feedback. Implicit signals (re-execution, undo, manual correction) are noisy.
- **Overfitting:** A single correction might not generalise. Weighting new signals against accumulated history is non-trivial.
- **Privacy:** Usage patterns are sensitive. All learning data must be local, encrypted, and deletable.

**Success Criteria:**
- Users can correct a tool result and see the correction persist for similar future requests
- False positive rate (incorrectly adapting based on noise) < 5%
- All learning data is local-only and deletable by the user

---

### 3.5 Linux Support (Beta)

**Category:** Short Term  
**Vision:** Eve OS runs on Ubuntu 24.04 LTS and Fedora 40 with feature parity for core workflows (chat, tools, permissions). Desktop integration adapts to GNOME and KDE.

**Motivation:** The architecture is cross-platform by design (Python backend, React frontend, Tauri shell). Locking to Windows limits the user base and contradicts the vision of a universal AI co-pilot. Linux developers are a natural early-adopter audience.

**Dependencies:**
- Windows Adapter abstraction layer (ADR-0001 — implemented)
- Linux-specific adapter implementation (must be built)
- Linux desktop integration (tray, notifications, hotkeys via D-Bus)

**Complexity:** Medium  
**Priority:** P2

**Estimated Milestone:** v1.1 (beta), Q4 2026

**Risks:**
- **Linux fragmentation:** Supporting multiple distributions, desktop environments, and package formats (.deb, .rpm, AppImage, Flatpak) is significant.
- **Tauri Linux maturity:** Tauri's Linux support is good but not at parity with Windows. System tray, global shortcuts, and notifications may have edge cases.
- **Python distribution:** Bundling Python on Linux is more complex than Windows. System Python versions vary widely.

**Success Criteria:**
- Ubuntu 24.04 LTS: all core features working
- Fedora 40: all core features working
- Linux-specific adapter for notifications, tray, and hotkeys
- Installation via .deb and .rpm

---

## 4. Version 1.5 — Connected Intelligence

**Target:** 6-9 months post-v1.0 (Q1–Q2 2027)  
**Theme:** Connect devices, enable cloud features (opt-in), deepen intelligence.  
**Risk Level:** Medium — introduces network dependencies and new infrastructure.

---

### 4.1 Cloud Sync (Opt-In)

**Category:** Medium Term  
**Vision:** Users optionally sync conversations, memory, settings, and installed plugins across devices. Sync is end-to-end encrypted. No data touches the server in plaintext. Users can choose what to sync. Fully offline operation continues without degradation when sync is off.

**Motivation:** A desktop assistant tied to one machine loses value when users switch between work and personal devices. Sync is the foundation for multi-device, team collaboration, and backup. It must be opt-in, transparently encrypted, and never mandatory.

**Dependencies:**
- Device identity system (ADR-0015 — Draft)
- Cloud backend infrastructure (new — server, database, auth)
- Encryption key management (device-bound + passphrase, ADR-0015)
- Conflict resolution strategy (last-write-wins per entity, per-field merge for settings)

**Complexity:** Very High  
**Priority:** P1

**Estimated Milestone:** v1.5, Q1 2027

**Risks:**
- **Trust:** Users must trust Eve with their data in the cloud. End-to-end encryption and open-source server code mitigate this but don't eliminate it.
- **Infrastructure cost:** Sync server costs scale with user base. Must be sustainable before launch.
- **Conflict resolution:** Concurrent edits on two devices lead to conflicts. CRDTs or operational transforms add significant complexity.

**Success Criteria:**
- End-to-end encryption verified by independent audit
- Sync latency < 5s (same region) for text content
- Conflict resolution handles 99% of cases automatically without user intervention
- Users can audit what data is synced and delete cloud data independently of local data

---

### 4.2 Multi-Device

**Category:** Medium Term  
**Vision:** Eve is installed on 2+ machines. Conversations and memory follow the user. Start a workflow on desktop, continue on laptop. All devices share the same knowledge graph, settings, and plugins.

**Motivation:** Single-device support limits Eve to a desktop-only assistant. Multi-device support (desktop + laptop, and eventually other form factors) makes Eve a persistent co-pilot that follows the user.

**Dependencies:**
- Cloud Sync (4.1 — required foundation)
- Device identity + pairing mechanism
- Cross-device state reconciliation

**Complexity:** High  
**Priority:** P2

**Estimated Milestone:** v1.5, Q2 2027

**Risks:**
- **Device pairing UX:** Must be simple (QR code, link code) and secure (device verification).
- **State conflict:** Same tool running on two devices simultaneously — unclear semantics.
- **Plugin sync:** Plugin binaries are platform-specific (Windows vs Linux plugin). Cross-platform plugin ecosystem needed.

**Success Criteria:**
- 2+ devices can be paired in under 60 seconds
- Conversation started on device A is accessible on device B within 10 seconds
- User can switch between devices mid-conversation without context loss

---

### 4.3 RAG Pipeline

**Category:** Medium Term  
**Vision:** Eve retrieves relevant information from the user's knowledge graph, past conversations, and indexed files before answering. Answers are grounded in the user's context, not just the AI model's training data. Sources are cited. Users can verify claims.

**Motivation:** AI models have a knowledge cutoff and no access to the user's personal context. RAG (Retrieval-Augmented Generation) bridges this gap. Every answer can reference the user's own data, making Eve truly personal.

**Dependencies:**
- Semantic Search (3.2 — vector index infrastructure)
- Personal Knowledge Graph (3.3 — knowledge base)
- AI Router with context window management (ADR-0003)
- Document indexing pipeline (new — extract text from PDF, DOCX, code)

**Complexity:** Very High  
**Priority:** P1

**Estimated Milestone:** v1.5, Q1–Q2 2027

**Risks:**
- **Retrieval quality:** Bad retrieval = bad answers. Chunking strategy, embedding model, and reranking all matter.
- **Context window limits:** Packing too much retrieved content into the prompt degrades answer quality and increases cost.
- **Citation accuracy:** AI models may hallucinate citations or misattribute sources.

**Success Criteria:**
- RAG answers include source citations with > 90% accuracy on a curated test set
- Retrieval precision@5 > 0.85
- End-to-end latency (query → retrieval → generation → response) < 5s

---

### 4.4 Knowledge Graph Reasoning

**Category:** Medium Term  
**Vision:** Eve answers questions that require multi-hop reasoning across the knowledge graph. "Which project did I work on after finishing the database migration?" "What tools did I use for that project?" Eve traverses graph relationships to find answers that no single document contains.

**Motivation:** Direct lookup handles "find me the conversation about X." Graph reasoning handles "find me the project that resulted from that conversation." This is the difference between a search engine and an intelligent assistant that understands relationships.

**Dependencies:**
- Personal Knowledge Graph (3.3 — populated graph)
- Graph traversal algorithms (ADR-0008, Memory Core — implemented)
- AI Router for natural language to graph query translation

**Complexity:** High  
**Priority:** P2

**Estimated Milestone:** v1.5, Q2 2027

**Risks:**
- **Query translation accuracy:** Translating "which project did I work on after the migration?" to a graph query is a hard NLU problem.
- **Graph completeness:** Answers are only as good as the graph. Sparse graphs produce poor reasoning results.
- **Explainability:** Users need to understand how Eve arrived at an answer. Graph traversal paths must be visualisable.

**Success Criteria:**
- Multi-hop questions answered correctly > 75% of the time on a curated knowledge graph
- Reasoning paths are visualisable in the UI
- Query translation adds < 2s overhead to response time

---

### 4.5 API Server

**Category:** Medium Term  
**Vision:** Eve exposes a documented REST API and WebSocket endpoint. External tools (IDEs, CI systems, custom scripts) can query memory, execute tools, and start conversations programmatically. API is authenticated and permission-scoped.

**Motivation:** The internal REST API (FastAPI on port 8456) already exists for the frontend. Exposing a public API enables integration with the broader tool ecosystem — VS Code extension, GitHub Actions, Slack bot, Zapier connector.

**Dependencies:**
- API authentication mechanism (API tokens + device identity — ADR-0015)
- Rate limiting per token (existing infrastructure — configurable)
- API documentation (OpenAPI — auto-generated by FastAPI)
- Permission scoping (API tokens inherit user permission level)

**Complexity:** Medium  
**Priority:** P2

**Estimated Milestone:** v1.5, Q1 2027

**Risks:**
- **Security:** An open API on localhost is an attack surface. Must be locked down by default, opt-in to expose.
- **API stability:** Once public, breaking changes are costly. API versioning strategy must be solid.
- **WebSocket lifecycle:** Long-lived connections for streaming responses need reconnection logic in clients.

**Success Criteria:**
- REST API documented with OpenAPI and published
- 3 reference integrations built (VS Code extension, CLI client, Python SDK)
- API authentication and rate limiting verified by security review
- Breaking changes require 1 version deprecation notice

---

### 4.6 macOS Support

**Category:** Medium Term  
**Vision:** Eve OS runs on macOS (Sonoma+). Feature parity with Windows for core workflows. macOS-specific design patterns (menu bar, Spotlight-like palette, native notifications, Touch Bar support).

**Motivation:** macOS is the second-largest desktop platform and the primary platform for developers — Eve's core audience. Cross-platform support validates the architectural decision to use Tauri and cross-platform Python.

**Dependencies:**
- macOS-specific adapter (replaces Windows Adapter — file system, process, notifications)
- macOS-specific desktop integration (menu bar, Dock, Spotlight)
- Tauri macOS maturity verification

**Complexity:** High  
**Priority:** P2

**Estimated Milestone:** v1.5, Q2 2027

**Risks:**
- **macOS permission model:** macOS permission system (accessibility, filesystem, automation) is significantly different from Windows. Each requires user-facing permission flows.
- **Python distribution on macOS:** Notarization, code signing for Python binaries. M-series compatibility.
- **Feature parity:** Some Windows-specific features (registry, Windows UI automation via PyAutoGUI) have no macOS equivalent. Feature parity expectations must be managed.

**Success Criteria:**
- macOS Sonoma: all core features working
- macOS-specific: Spotlight-like command palette integration
- macOS adapter for notifications, menu bar, file system, and process management
- Distribution via .dmg

---

### 4.7 Self Learning (Advanced)

**Category:** Medium Term — Experimental  
**Vision:** Eve continuously improves from usage patterns without explicit user feedback. Frequently used tools get ranked higher. Rarely used capabilities get deprioritised. Response style adapts to user preferences (verbosity, formality, technical depth).

**Motivation:** Basic self-learning (3.4) requires explicit user feedback (thumbs up/down). Advanced self-learning infers preferences from implicit signals: which results the user reads fully, which they dismiss, which they act on. This is the difference between a reactive assistant and one that anticipates.

**Dependencies:**
- Basic self-learning infrastructure (3.4 — feedback loop)
- Usage analytics pipeline (local-only, privacy-preserving)
- Preference model (learned from implicit signals)
- AI Router integration (preference-weighted provider selection)

**Complexity:** Very High  
**Priority:** P3

**Estimated Milestone:** v1.5, Q2 2027 (experimental)

**Risks:**
- **Privacy:** Implicit signals are more sensitive than explicit feedback. Everything Eve observes about user behaviour must be local-only and transparent.
- **Noise:** Not all dismissals are negative. The user may have already read the information elsewhere. Distinguishing signal from noise is hard.
- **Bias amplification:** Self-learning can create filter bubbles — the system optimises for what the user already does, not for what they might want to discover.

**Success Criteria:**
- System detects 3 implicit preference signals (dwell time, re-execution, dismissal) with > 80% accuracy
- Preference model improves response relevance by 20% (measured by user satisfaction survey)
- All learning data is local-only, encrypted, and user-deletable

---

## 5. Version 2.0 — Autonomous Platform

**Target:** 12-18 months post-v1.0 (Q3–Q4 2027)  
**Theme:** Multi-agent systems, team collaboration, enterprise readiness.  
**Risk Level:** High — introduces multi-user, multi-agent, and enterprise compliance.

---

### 5.1 AI Agents

**Category:** Long Term  
**Vision:** Users create, configure, and deploy specialised AI agents. Each agent has its own persona, tool access, memory scope, and permission level. Agents can be assigned to recurring tasks (monitor a directory, check for updates, summarise daily activity). Users interact with agents via the same chat interface.

**Motivation:** The current architecture has one AI "brain" per session. Multi-agent architecture enables: specialised agents (code agent, research agent, sysadmin agent), parallel task execution, and separation of concerns. Each agent can be configured independently without affecting the others.

**Dependencies:**
- Execution Engine with parallel plan support (ADR-0011 — implemented)
- Capability Registry for agent-specific capability scoping (ADR-0004 — implemented)
- Memory scoping (ADR-0007 — per-agent memory spaces)
- Agent lifecycle management (new — create, configure, pause, terminate)
- Agent communication protocol (new — agents can delegate to each other)

**Complexity:** Very High  
**Priority:** P1

**Estimated Milestone:** v2.0, Q3 2027

**Risks:**
- **Coordination complexity:** Multiple agents acting semi-autonomously can conflict (two agents trying to write to the same file).
- **User confusion:** "Which agent am I talking to?" The UX must make agent identity crystal clear.
- **Resource contention:** N agents each consuming AI model tokens, tool execution slots, and memory bandwidth.
- **Security scope creep:** An agent with broad permissions can be a vulnerability. Agent permissions must be strictly scoped and auditable.

**Success Criteria:**
- 3 pre-built agent templates ship with v2.0 (Assistant, Code Helper, System Monitor)
- Users can create custom agents with selected tools and memory scope
- Agents run recurring tasks independently without user supervision
- Agent activity is fully auditable (which agent did what, when, with which permissions)

---

### 5.2 Team Collaboration

**Category:** Long Term  
**Vision:** Multiple users share an Eve workspace. Team members see each other's conversations (scoped to shared projects), share memory and tools, and collaborate on multi-step workflows. Permissions are team-aware: managers can configure what tools and data the team can access.

**Motivation:** Eve is designed as a personal co-pilot. Many use cases are inherently collaborative: team standup summaries, shared project tracking, collaborative code review, incident response. A single-user assistant misses this entire category.

**Dependencies:**
- Cloud Sync (4.1 — device-to-cloud sync)
- Multi-Device (4.2 — sync infrastructure)
- Shared Memory (5.3 — multi-user memory spaces)
- Authentication (ADR-0015 — extended for multi-user)
- Team management infrastructure (new — teams, roles, invitations)

**Complexity:** Very High  
**Priority:** P2

**Estimated Milestone:** v2.0, Q4 2027

**Risks:**
- **Trust model:** Team collaboration requires data to be stored on a server. This is a fundamental shift from the local-first model. Must be strictly opt-in per team.
- **Privacy:** Team members sharing a workspace raises privacy boundaries. Personal conversation vs team conversation must be clearly delineated.
- **Compliance:** Enterprise teams may have compliance requirements (data residency, audit trails, retention policies).

**Success Criteria:**
- 3+ users can collaborate in a shared workspace
- Shared memory and tools accessible to all team members (scoped)
- Permission management: team owner configures tool access per user
- Personal and team conversations are clearly separated

---

### 5.3 Shared Memory

**Category:** Long Term  
**Vision:** Teams share a knowledge graph. What one team member learns is available to all. Entities (projects, clients, processes) have team-wide context. Knowledge persists across team member turnover — new members benefit from accumulated team memory.

**Motivation:** Personal knowledge graphs (3.3) are powerful for individuals. Shared memory extends this to teams — institutional knowledge that survives individual departures. "What did we learn about deploying to that client's environment?" becomes a query, not a meeting.

**Dependencies:**
- Personal Knowledge Graph (3.3 — graph infrastructure)
- Cloud Sync (4.1 — remote storage)
- Team Collaboration (5.2 — team concept)
- Multi-user memory isolation and merging (new)
- Conflict resolution for concurrent knowledge contributions

**Complexity:** Very High  
**Priority:** P2

**Estimated Milestone:** v2.0, Q4 2027

**Risks:**
- **Information overload:** Team memory grows faster than personal memory. Filtering, scoping, and importance ranking are critical.
- **Trust and accuracy:** A team member may contribute incorrect knowledge. Source attribution and correction mechanisms needed.
- **Orphaned knowledge:** When a team member leaves, their contributed knowledge remains but its context (who, why) is lost.

**Success Criteria:**
- Team knowledge graph is automatically populated from all team members' activities
- Team memory query returns results with source attribution (who contributed)
- New team member onboarding time reduced by 30% (measured by survey)
- Knowledge quality maintained via user correction and voting

---

### 5.4 Workflow Marketplace

**Category:** Long Term  
**Vision:** Users browse, install, and customise pre-built workflows. "Summarise my day," "Deploy to staging," "Audit system health" — complex multi-tool workflows available as one-click templates. Community contributors publish and share workflows.

**Motivation:** Individual tools are powerful, but the real value is in combining them. A workflow marketplace captures best practices as reusable templates. Users get complex automation without understanding the underlying tools. This is Eve's "spreadsheet macro" ecosystem.

**Dependencies:**
- Plugin Marketplace (3.1 — distribution infrastructure)
- Execution Engine with plan persistence (ADR-0011 — implemented)
- Workflow template format (new — serialised execution plans with parameter slots)
- Workflow editor UI (new — visual or text-based workflow builder)

**Complexity:** High  
**Priority:** P2

**Estimated Milestone:** v2.0, Q4 2027

**Risks:**
- **Workflow fragility:** Workflows that depend on specific tool versions or system configurations break over time.
- **Security:** Automated workflows that execute sensitive operations are attractive targets. Permission model must extend to workflow-level.
- **Quality variance:** Community workflows vary in quality. Rating system, testing pipeline, and curation needed.

**Success Criteria:**
- 20+ community workflows published within 1 month of launch
- Workflows can be installed, customised (parameterised), and executed
- Workflow execution is audited and permission-gated
- Workflow editor enables non-developers to create simple workflows

---

### 5.5 Enterprise Suite

**Category:** Long Term  
**Vision:** SSO (SAML/OIDC), role-based access control (RBAC), audit logging, compliance reporting (SOC 2, HIPAA), data residency controls, dedicated support SLA. Eve meets enterprise procurement requirements out of the box.

**Motivation:** Enterprise adoption requires more than a great product. Procurement demands: "Do you have SSO? Audit logs? SOC 2? Data residency?" Without these, enterprise deals are blocked regardless of product quality.

**Dependencies:**
- Authentication model (ADR-0015 — extended for SSO)
- Cloud Sync (4.1 — enterprise server deployment)
- Team Collaboration (5.2 — RBAC extension)
- Audit logging infrastructure (new — append-only, tamper-evident logs)
- Compliance documentation (SOC 2 Type II, HIPAA BAA)

**Complexity:** Very High  
**Priority:** P3

**Estimated Milestone:** v2.0, Q4 2027

**Risks:**
- **SSO integration complexity:** Each IdP (Okta, Azure AD, OneLogin) has quirks. SAML is notoriously implementation-specific.
- **Compliance cost:** SOC 2 Type II audit costs $30k-100k+ annually. Must be justified by enterprise revenue.
- **Self-hosted vs cloud:** Enterprise may require self-hosted deployment. This is a fundamentally different operational model.

**Success Criteria:**
- SSO with Okta and Azure AD verified
- RBAC with 3 pre-defined roles (Admin, Member, Viewer)
- Audit logs capture all tool executions, permission grants, and config changes
- SOC 2 Type II report published
- 3 enterprise customers in production

---

## 6. Version 3.0 — Distributed Ecosystem

**Target:** 24+ months post-v1.0 (2028+)  
**Theme:** Decentralised agents, remote execution, peer-to-peer.  
**Risk Level:** Very High — depends on ecosystem maturity and market readiness.

---

### 6.1 Distributed Agents

**Category:** Long Term — Research  
**Vision:** Agents run on multiple machines in a peer-to-peer network. An agent on a build server can trigger an agent on a test server, which reports to an agent on the developer's desktop. Agents discover each other via a registry, authenticate via device identity, and communicate via encrypted channels.

**Motivation:** The most powerful workflows span machines: build on a CI server, test on a staging environment, deploy to production, monitor on a dashboard. Distributed agents enable cross-machine orchestration without a central server.

**Dependencies:**
- AI Agents (5.1 — agent model)
- Cloud Sync (4.1 — connectivity)
- Authentication (ADR-0015 — extended for machine-to-machine)
- Peer-to-peer communication protocol (new — WebRTC or similar)
- Agent registry (new — decentralised or hub-based)

**Complexity:** Very High  
**Priority:** P3

**Estimated Milestone:** v3.0, 2028+

**Risks:**
- **Network complexity:** NAT traversal, firewalls, dynamic IPs. Peer-to-peer connectivity in enterprise networks is notoriously difficult.
- **Security model:** Machine-to-machine auth is harder than user auth. Compromised agent = compromised network.
- **Reliability:** Distributed systems fail in complex ways. Partition tolerance, eventual consistency, and graceful degradation are required.

**Success Criteria:**
- 2+ machines can discover and communicate with each other via peer-to-peer
- Agent on machine A can trigger a tool execution on machine B
- End-to-end encryption for all inter-agent communication
- Network partition does not cause data loss

---

### 6.2 Remote Execution

**Category:** Long Term — Experimental  
**Vision:** Users execute tools on remote machines (SSH hosts, cloud VMs, Raspberry Pis) as if they were local. File operations, script execution, system monitoring — all available via the same Eve interface. Remote machines are managed, monitored, and accessible from the Eve dashboard.

**Motivation:** Developers manage multiple machines. Operations teams manage dozens. Remote execution brings Eve's tool ecosystem to the entire infrastructure, not just the local desktop.

**Dependencies:**
- API Server (4.5 — remote access pattern)
- Distributed Agents (6.1 — inter-machine communication)
- Authentication model extended for remote hosts
- SSH/WinRM adapter (new)

**Complexity:** Very High  
**Priority:** P3

**Estimated Milestone:** v3.0, 2028+

**Risks:**
- **Security:** Remote execution is the highest-risk feature on this roadmap. Every remote command is an attack surface. Bastion host pattern required.
- **Latency:** Remote execution over high-latency links (100ms+ RTT) breaks the interactive feel.
- **Firewall traversal:** Enterprise networks block SSH/WinRM. Alternative connectivity (WebSocket relay, VPN) needed.

**Success Criteria:**
- SSH remote execution: commands, file operations, and system monitoring
- Remote machines appear in the Eve dashboard with status indicators
- Execution latency < 2x local latency (excluding network overhead)
- Security review passes with no high-risk findings

---

## 7. Research & Experimental

These items are actively investigated but have no committed timeline. They may become roadmap items, merge with other items, or be cancelled.

---

### R.1 Distributed Agent Coordination Protocol

**Category:** Research  
**Description:** Design a protocol for agents to discover each other, delegate tasks, share context, and report results. The protocol must be secure, decentralised (no central broker), and efficient (low overhead per message).

**Current Status:** Problem definition phase. Evaluating existing protocols (NATS, MQTT, gRPC streams, custom WebSocket-based) against requirements.

**Success Criteria for Exit:** Protocol design document approved. Reference implementation connects 2 agents. Bandwidth overhead < 5% of payload size.

---

### R.2 Self-Learning without Explicit Feedback

**Category:** Research  
**Description:** Infer user preferences and intent from implicit signals only (no thumbs up/down). Evaluate gaze tracking (via webcam), dwell time analysis, scroll behaviour, re-execution patterns, and edit distance on tool parameters.

**Current Status:** Literature review. Evaluating feasibility of privacy-preserving implicit signal collection.

**Success Criteria for Exit:** 3+ implicit signals identified with measurable correlation to user satisfaction. Prototype demonstrates 15% improvement in tool ranking relevance. Privacy review passes.

---

### R.3 Graph Neural Networks for Knowledge Reasoning

**Category:** Research  
**Description:** Apply graph neural networks (GNNs) to the personal knowledge graph for link prediction (what should Eve suggest next?), node classification (which projects are active?), and anomaly detection (which tools are behaving unexpectedly?).

**Current Status:** Feasibility study. GNNs require labelled training data. Evaluating whether synthetic data generation from interaction logs is viable.

**Success Criteria for Exit:** GNN model outperforms heuristic baselines by 20% on link prediction. Training pipeline runs entirely on-device (no cloud dependency). Inference latency < 100ms.

---

### E.1 Voice-Activated Autonomous Mode

**Category:** Experimental  
**Description:** Full voice-controlled operation. User speaks a goal, Eve plans and executes autonomously, reporting progress via voice. "Eve, deploy the latest build to staging and run the test suite."

**Current Status:** Voice pipeline exists (STT + TTS). Autonomous mode requires the full execution engine chain. Integration proof-of-concept planned.

**Success Criteria for Exit:** 3 voice-triggered autonomous workflows tested end-to-end. Voice recognition accuracy > 95% in quiet environment. Response latency < 3s.

---

### E.2 Visual Workflow Builder

**Category:** Experimental  
**Description:** Drag-and-drop workflow construction. Users compose tools, conditions, and loops visually. Generated workflows are serialised to the same format as coded workflows.

**Current Status:** UX prototype. Evaluating node-graph editor libraries (React Flow, Blockly, custom).

**Success Criteria for Exit:** Non-developer user can create a 3-step workflow in under 5 minutes. Generated workflow is indistinguishable from a coded workflow.

---

## 8. Deferred

These capabilities are deliberately postponed. They are not cancelled — they will be reconsidered at each major version planning cycle.

---

### D.1 Mobile Companion App

**Reason Deferred:** The core value proposition — autonomous desktop AI — does not translate to mobile. Mobile notifications and voice queries are feasible but the full tool execution model requires desktop OS access. A mobile companion risks diluting focus.

**Re-evaluation Trigger:** Cloud Sync (4.1) reaches maturity and there is demonstrated user demand for mobile notifications.

---

### D.2 Full Cloud Offering (SaaS)

**Reason Deferred:** Contradicts the local-first principle that defines Eve. Many users chose Eve specifically because it runs locally. A SaaS version would create a fundamentally different product with different privacy, security, and pricing models.

**Re-evaluation Trigger:** Enterprise survey indicates > 30% of prospects require SaaS deployment and cannot use self-hosted.

---

### D.3 Browser Extension

**Reason Deferred:** Browser automation already exists (Playwright-based). A browser extension would enable richer integration (context menu, page content access) but requires per-browser development (Chrome, Firefox, Edge) and ongoing maintenance against browser API changes.

**Re-evaluation Trigger:** Users request browser-integrated features (page summarisation, form filling, research assistant) that Playwright automation cannot provide.

---

### D.4 On-Premise Enterprise Server

**Reason Deferred:** Self-hosted enterprise deployment requires significant infrastructure: containerisation, orchestration, backup/restore, monitoring, multi-tenancy, and enterprise support SLAs. Premature investment before product-market fit in the enterprise segment.

**Re-evaluation Trigger:** 5+ enterprise customers in production via the standard cloud offering.

---

### D.5 Multi-User Real-Time Collaboration (Google Docs-style)

**Reason Deferred:** Real-time collaboration (multiple users editing the same conversation or workflow simultaneously) is a massive engineering investment (CRDTs, WebSocket sync, presence). The value for an AI assistant is unclear compared to async collaboration patterns.

**Re-evaluation Trigger:** User research demonstrates that real-time collaboration is a top-3 requested feature for team workspaces.

---

## 9. Dependency Map

```
v1.0 ─────────────────────────────────────────────────────────────────
  │
  ├── Plugin SDK ─────────► Plugin Marketplace (v1.1)
  │
  ├── SQLite + Vector ────► Semantic Search (v1.1)
  │                              │
  │                              └────────► RAG Pipeline (v1.5)
  │
  ├── Memory Core ─────────► Knowledge Graph (v1.1) ──► Graph Reasoning (v1.5)
  │                              │
  │                              └──────────────────────────► Shared Memory (v2.0)
  │
  ├── Event Bus ───────────► Activity Center (v1.0)
  │                              │
  │                              └────────► Distributed Agents Protocol (R.1)
  │
  ├── Windows Adapter ─────► Linux Adapter (v1.1) ──► macOS Adapter (v1.5)
  │
  └── Auth (draft) ────────► Cloud Sync (v1.5) ──► Team Collab (v2.0)
                                 │                        │
                                 ├► Multi-Device (v1.5)   │
                                 │                        ├► Enterprise (v2.0)
                                 └────────────────────────┘
```

### 9.1 Critical Path Items

Items that unblock the most downstream capabilities:

| Item | Unblocks | If Delayed |
|------|----------|------------|
| Plugin Marketplace | Workflow Marketplace, Plugin Ecosystem | Ecosystem growth stalls |
| Knowledge Graph | Graph Reasoning, RAG, Shared Memory | Intelligence plateau |
| Cloud Sync | Multi-Device, Team Collab, Enterprise | Collaboration features blocked |
| AI Agents | Distributed Agents, Remote Execution | Autonomy vision blocked |

---

## 10. Appendix A — Capability Maturity Model

Each capability evolves through 4 maturity levels:

| Level | Label | Meaning |
|-------|-------|---------|
| L1 | Foundation | Works but requires expertise. CLI-only, no UI, no documentation. |
| L2 | Usable | Has a UI, basic documentation, works for common cases. |
| L3 | Delightful | Polished UX, comprehensive docs, handles edge cases, performant. |
| L4 | Platform | Extensible via API/SDK, ecosystem of integrations, community. |

### Current vs Target Maturity

| Capability | v1.0 | v1.1 | v1.5 | v2.0 | v3.0 |
|------------|------|------|------|------|------|
| Plugin System | L2 | L3 | L3 | L4 | L4 |
| Semantic Search | L1 | L2 | L3 | L3 | L3 |
| Knowledge Graph | L1 | L2 | L2 | L3 | L3 |
| Self Learning | — | L1 | L2 | L2 | L3 |
| Cloud Sync | — | — | L2 | L3 | L3 |
| Multi-Device | — | — | L2 | L3 | L3 |
| RAG | — | — | L2 | L3 | L3 |
| AI Agents | — | — | L1 | L2 | L3 |
| Team Collaboration | — | — | — | L2 | L3 |
| Enterprise | — | — | — | L2 | L3 |
| Distributed Agents | — | — | — | — | L2 |

---

## 11. Appendix B — Risk Registry

### Active Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-001 | Plugin ecosystem fails to gain traction | Medium | High | Invest in plugin developer experience, provide reference plugins, seed marketplace with first-party plugins |
| R-002 | Cloud sync adoption low due to trust concerns | Medium | High | Open-source server code, publish security audit, E2E encryption by default |
| R-003 | AI model costs make RAG economically unviable | Low | Very High | Local embedding models, caching, tiered retrieval (cheap first, expensive second) |
| R-004 | Enterprise sales cycle too long for current runway | Medium | Very High | Focus on SMB self-serve first, enterprise as FY+2 play |
| R-005 | Cross-platform maintenance burden exceeds capacity | Medium | High | Shared adapter interface, CI per platform, community contributions for non-primary platforms |
| R-006 | Knowledge graph quality fails to meet user expectations | Medium | High | Conservative confidence thresholds, user-visible confidence indicators, manual correction flow |
| R-007 | Multi-agent conflicts cause unpredictable behaviour | High | Medium | Strict agent permission scoping, conflict detection, user override, agent sandboxing |

### Retired Risks

| ID | Risk | Retired In | Reason |
|----|------|-----------|--------|
| R-000 | Python backend can't meet performance requirements | v1.0 | Benchmarks show sub-second response times for all P0 operations |
| R-000 | React frontend bundle too large for Tauri webview | v1.0 | Bundle size < 200KB gzipped |
| R-000 | SQLite can't handle expected data volume | v1.0 | Tested with 100k+ entries, query times within budget |

---

*This roadmap is a living document. It is reviewed and updated every quarter as part of the release planning process. Items may be added, removed, reprioritised, or deferred based on user feedback, market conditions, and engineering realities.*

# System Architecture

**Document ID:** 02-System-Architecture  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document defines the high-level system architecture of AIOS, including component relationships, communication flows, and design patterns.

## 2. High-Level Architecture

AIOS follows a **layered, event-driven architecture** with clear separation of concerns.

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[Desktop UI - Tauri/React]
        Voice[Voice Interface]
        Notif[Notification System]
    end

    subgraph "Core Layer"
        EB[Event Bus]
        AR[AI Router]
        PL[Planner]
        TM[Tool Manager]
        PM[Permission Manager]
        MS[Memory System]
        CE[Context Engine]
        CS[Conversation System]
    end

    subgraph "Adapter Layer"
        WA[Windows Adapter]
        VS[Vision System]
        PS[Plugin SDK]
    end

    subgraph "Infrastructure"
        DB[(SQLite)]
        FS[File System]
        Config[Configuration]
        Log[Logging]
    end

    UI[User Interface] --> CS
    CS --> EB
    EB --> AR
    AR --> PL
    PL --> TM
    TM --> PM
    PM --> WA
    PM --> VS
    EB --> CE
    EB --> MS[Memory System]
    WA --> Windows[Windows OS]
    PS --> TM
```

## 4. Layered Architecture

```mermaid
graph TB
    subgraph "Layer 1: Presentation"
        UI[React/Tauri UI]
        Voice[Voice Interface]
        Notif[Notifications]
    end

    subgraph "Layer 2: Conversation"
        Chat[Chat Manager]
        VoiceIn[Voice Input]
        Context[Context Engine]
    end

    subgraph "Layer 3: Intelligence"
        Router[AI Router]
        Planner[Planner]
        Memory[Memory System]
    end

    subgraph "Layer 4: Execution"
        Tools[Tool Manager]
        Perms[Permission Manager]
        Plugins[Plugin SDK]
    end

    subgraph "Layer 5: Adapter"
        Win[Windows Adapter]
        Vision[Vision System]
    end

    subgraph "Layer 6: Infrastructure"
        Events[Event Bus]
        DB[(SQLite)]
        FS[File System]
    end

    UI[User] --> Layer2
    Layer2 --> Layer3
    Layer3 --> Layer4
    Layer4 --> Layer5
    Layer5 --> Windows[Windows OS]
    Layer6 -.-> All[All Layers]
```

## 5. Event-Driven Architecture

```mermaid
graph LR
    subgraph "Event Producers"
        UI[User Interface]
        CE[Context Engine]
        TM[Tool Manager]
        PM[Permission Manager]
        VS[Vision System]
    end

    subgraph "Event Bus"
        EB[Event Bus]
        Q[Message Queue]
    end

    subgraph "Event Consumers"
        AR[AI Router]
        PL[Planner]
        MS[Memory System]
        CS[Conversation System]
        LOG[Logger]
    end

    UI -->|user:message| EB
    CE -->|context:changed| EB
    TM -->|tool:executed| EB
    PM -->|permission:granted| EB
    VS -->|vision:captured| EB
    EB --> AR
    EB --> PL
    EB --> MS
    EB --> CS
    EB --> LOG
```

## 6. Communication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant WA as Windows Adapter

    U->>UI: "Find large files and compress them"
    UI->>CS: Process message
    CS->>EB: user:message
    EB->>AR: route:request
    AR->>AR: Select AI provider
    AR->>PL: plan:create
    PL->>PL: Decompose task
    PL->>TM: Execute step 1: find files
    TM->>PM: Request permission
    PM->>UI: Show permission dialog
    U->>PM: Approve
    PM->>TM: Permission granted
    TM->>WA: Execute find
    WA-->>TM: Results
    TM->>PL: Step complete
    PL->>TM: Execute step 2: compress
    TM->>PM: Request permission
    PM->>UI: Show permission dialog
    U->>PM: Approve
    PM->>TM: Permission granted
    TM->>WA: Execute compress
    WA-->>TM: Results
    TM->>PL: Step complete
    PL->>CS: Task complete
    CS->>UI: Show result
```

## 7. Module Dependencies

```mermaid
graph LR
    subgraph "Core Dependencies"
        UI[UI Layer] --> CS[Conversation System]
        CS --> EB[Event Bus]
        EB --> AR[AI Router]
        AR --> PL[Planner]
        PL --> TM[Tool Manager]
        TM --> PM[Permission Manager]
    end

    subgraph "Supporting Modules"
        CE[Context Engine] --> EB
        MS[Memory System] --> EB
        VS[Vision System] --> TM
        WA[Windows Adapter] --> TM
        PS[Plugin SDK] --> TM
    end

    subgraph "Infrastructure"
        EB --> LOG[Logger]
        EB --> DB[(Database)]
        EB --> CFG[Config]
    end
```

## 7. Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| **UI Layer** | React-based desktop interface, command palette, chat, notifications |
| **Conversation System** | Manages chat lifecycle, voice input, message routing |
| **Event Bus** | Decoupled communication between all modules |
| **AI Router** | Routes requests to AI providers, handles failover |
| **Planner** | Decomposes tasks, manages execution graph, handles recovery |
| **Tool Manager** | Registers, validates, and executes tools |
| **Permission Manager** | Gates all tool execution through permission levels |
| **Memory System** | Short-term, long-term, and semantic memory |
| **Context Engine** | Tracks active applications, files, and user activity |
| **Windows Adapter** | Abstracts Windows API calls behind a safe interface |
| **Vision System** | OCR, screenshot capture, UI understanding |
| **Plugin SDK** | Third-party tool and event registration |
| **Event Bus** | Decoupled inter-module communication |

## 8. Data Flow: User Request

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant WA as Windows Adapter

    User->>UI: "Find all PDFs larger than 10MB"
    UI->>CS: Send message
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR->>AR: Select provider
    AR->>PL: plan:create
    PL->>PL: Decompose into steps
    PL->>TM: execute(find_files, {ext: "pdf", minSize: "10MB"})
    TM->>PM: check_permission
    PM->>UI: Show permission dialog
    User->>PM: Approve
    PM->>TM: permission:granted
    TM->>TM: Execute tool
    TM->>WA: windows:search_files
    WA-->>TM: File list
    TM-->>PL: Results
    PL->>CS: Format response
    CS->>UI: Display results
```

## 9. Design Patterns

| Pattern | Usage |
|---------|-------|
| **Event-Driven** | Inter-module communication via Event Bus |
| **Observer** | Modules subscribe to events they care about |
| **Strategy** | AI providers are swappable strategies |
| **Command** | Tool execution follows command pattern |
| **Chain of Responsibility** | Permission checks chain through levels |
| **Adapter** | Windows Adapter abstracts OS APIs |
| **Factory** | Tool and provider creation |
| **Singleton** | Event Bus, Database, Configuration |

## 10. Future Extensibility

- **New AI providers** — Add via AI Router strategy pattern
- **New tools** — Register via Tool Manager
- **New plugins** — SDK with manifest registration
- **New OS support** — Create new Adapter implementations
- **New input modes** — Voice, gesture, gaze — all feed into Conversation System

## 11. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Single point of failure (Event Bus) | High | Persistent queue, health checks |
| AI provider latency | Medium | Parallel routing, timeout, fallback |
| Plugin memory leaks | Medium | Sandboxed execution, resource limits |
| Windows API changes | Medium | Abstracted adapter layer |
| Permission fatigue | Medium | Smart defaults, session permissions |

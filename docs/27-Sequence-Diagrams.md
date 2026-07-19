# Sequence Diagrams

**Document ID:** 27-Sequence-Diagrams  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document provides end-to-end sequence diagrams for key AIOS workflows, serving as the definitive reference for system behavior.

## 2. Voice → Open VS Code

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant CR as Capability Registry
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant WA as Windows Adapter

    User->>UI: "Open VS Code" (voice)
    UI->>CS: voice_input
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR->>AR: Select provider
    AR-->>EB: ai:response
    EB->>PL: plan:create
    PL->>CR: find_capability("app.open")
    CR-->>PL: tool_id: "launch_app"
    PL->>TM: execute(launch_app, {name: "VS Code"})
    TM->>PM: check_permission(launch_app, safe)
    PM-->>TM: auto_approved
    TM->>WA: start_process("code")
    WA-->>TM: process_started
    TM-->>PL: success
    PL->>CS: task_complete
    CS->>UI: "VS Code is now open"
```

## 3. Chat → Summarize PDF

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant CR as Capability Registry
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant WA as Windows Adapter
    participant MS as Memory System

    User->>UI: "Summarize the PDF in my Downloads"
    UI->>CS: send_message
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR-->>EB: ai:response
    EB->>PL: plan:create
    PL->>CR: find_capability("file.search")
    CR-->>PL: tool_id: "search_files"
    PL->>TM: execute(search_files, {pattern: "*.pdf", path: "Downloads"})
    TM->>PM: check_permission(search_files, read)
    PM-->>TM: auto_approved
    TM->>WA: search_files
    WA-->>TM: [report.pdf]
    TM-->>PL: results
    PL->>CR: find_capability("file.read")
    CR-->>PL: tool_id: "read_file"
    PL->>TM: execute(read_file, {path: "report.pdf"})
    TM->>PM: check_permission(read_file, read)
    PM-->>TM: auto_approved
    TM->>WA: read_file
    WA-->>TM: content
    TM-->>PL: content
    PL->>AR: summarize(content)
    AR-->>PL: summary
    PL->>CS: task_complete
    CS->>UI: "Here's the summary..."
```

## 4. Screenshot → UI Analysis

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant CR as Capability Registry
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant VS as Vision System
    participant WA as Windows Adapter

    User->>UI: "What's on my screen?"
    UI->>CS: send_message
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR-->>EB: ai:response
    EB->>PL: plan:create
    PL->>CR: find_capability("vision.capture")
    CR-->>PL: tool_id: "capture_screen"
    PL->>TM: execute(capture_screen)
    TM->>PM: check_permission(capture_screen, read)
    PM-->>TM: auto_approved
    TM->>VS: capture_screen()
    VS->>WA: get_screenshot
    WA-->>VS: screenshot
    VS-->>TM: image
    TM-->>PL: screenshot
    PL->>CR: find_capability("vision.analyze")
    CR-->>PL: tool_id: "analyze_screen"
    PL->>TM: execute(analyze_screen, {image})
    TM->>VS: detect_ui_elements(image)
    VS-->>TM: elements
    TM-->>PL: ui_elements
    PL->>AR: describe_screen(ui_elements)
    AR-->>PL: description
    PL->>CS: task_complete
    CS->>UI: "You have VS Code, Chrome, and Terminal open..."
```

## 5. Browser Automation

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant CR as Capability Registry
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant PW as Playwright

    User->>UI: "Search for AIOS on Google"
    UI->>CS: send_message
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR-->>EB: ai:response
    EB->>PL: plan:create
    PL->>CR: find_capability("browser.search")
    CR-->>PL: tool_id: "web_search"
    PL->>TM: execute(web_search, {query: "AIOS"})
    TM->>PM: check_permission(web_search, safe)
    PM-->>TM: auto_approved
    TM->>PW: navigate("google.com")
    TM->>PW: search("AIOS")
    PW-->>TM: results
    TM-->>PL: search_results
    PL->>AR: summarize(results)
    AR-->>PL: summary
    PL->>CS: task_complete
    CS->>UI: "Here are the top results for AIOS..."
```

## 6. Plugin Execution

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant CR as Capability Registry
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant PMgr as Plugin Manager
    participant Plugin as Plugin Sandbox

    User->>UI: "Run my custom analysis"
    UI->>CS: send_message
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR-->>EB: ai:response
    EB->>PL: plan:create
    PL->>CR: find_capability("custom.analyze")
    CR-->>PL: tool_id: "my_plugin.analyze"
    PL->>TM: execute(my_plugin.analyze, {input: "data"})
    TM->>PM: check_permission(my_plugin.analyze, safe)
    PM-->>TM: auto_approved
    TM->>PMgr: execute_in_sandbox("my_plugin.analyze", params)
    PMgr->>Plugin: run(params)
    Plugin-->>PMgr: result
    PMgr-->>TM: sandbox_result
    TM-->>PL: result
    PL->>CS: task_complete
    CS->>UI: "Analysis complete: ..."
```

## 7. Memory Retrieval

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant MS as Memory System

    User->>UI: "What was I working on yesterday?"
    UI->>CS: send_message
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR->>MS: search("yesterday's work")
    MS->>MS: semantic_search(query)
    MS-->>AR: memories
    AR-->>EB: ai:response
    EB->>CS: response
    CS->>UI: "Yesterday you were working on the AIOS project..."
```

## 8. Coding Workflow

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant CS as Conversation System
    participant EB as Event Bus
    participant AR as AI Router
    participant PL as Planner
    participant CR as Capability Registry
    participant TM as Tool Manager
    participant PM as Permission Manager
    participant WA as Windows Adapter
    participant CE as Context Engine

    User->>UI: "Create a new React component called Header"
    UI->>CS: send_message
    CS->>EB: publish(user:message)
    EB->>AR: route:request
    AR-->>EB: ai:response
    EB->>PL: plan:create
    PL->>CE: get_current_context()
    CE-->>PL: {project: "/projects/my-app", type: "react"}
    PL->>CR: find_capability("file.create")
    CR-->>PL: tool_id: "create_file"
    PL->>TM: execute(create_file, {path: "/projects/my-app/src/Header.tsx"})
    TM->>PM: check_permission(create_file, workspace)
    PM-->>TM: session_approved
    TM->>WA: write_file
    WA-->>TM: file_created
    TM-->>PL: success
    PL->>AR: generate_component_code("Header")
    AR-->>PL: component_code
    PL->>TM: execute(write_file, {content: code})
    TM->>PM: check_permission(write_file, workspace)
    PM-->>TM: session_approved
    TM->>WA: write_file
    WA-->>TM: written
    TM-->>PL: success
    PL->>CS: task_complete
    CS->>UI: "Created Header.tsx component"
```

## 9. Implementation Notes

- All diagrams incorporate the Capability Registry as the discovery layer
- Permission checks are shown at their actual level
- Error paths are omitted for clarity (see 28-Error-Recovery.md)
- All inter-module communication goes through the Event Bus
- The Planner never knows specific tool IDs — it always queries capabilities

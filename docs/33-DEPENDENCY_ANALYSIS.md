# 33. Dependency Analysis

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  App.tsx → components/* → fetch(/api/v1/*)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                        API LAYER                              │
│  app.py → chat.py, tools.py, capabilities.py, settings.py    │
│           plugins.py, desktop.py, execution.py, workspace.py  │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
┌──────────┴──────────┴──────────┴──────────────────────────┐
│                  APPLICATION LAYER                          │
│  ConversationManager  ExecutionEngine  WorkspaceManager     │
│  ConversationService  PlannerAdapter   WorkspaceService     │
│  PluginManager        Planner          MemorySystem         │
│  ContextEngine        StatusService    SettingsStore         │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                      CORE LAYER                              │
│  EventBus  DIContainer  AIRouter  PermissionManager          │
│  ToolManager  CapabilityRegistry  ContextEngine              │
└─────────────────────────────────────────────────────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  Models  Interfaces  Exceptions  Events                      │
└─────────────────────────────────────────────────────────────┘

# Folder Structure

**Document ID:** 05-Folder-Structure  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document defines the project folder structure for AIOS and explains the purpose of every directory.

## 2. Top-Level Structure

```
aios/
├── src/                    # Source code
│   ├── frontend/           # React/TypeScript UI
│   ├── backend/            # Python backend
│   └── shared/            # Shared types and constants
├── plugins/                # Plugin directory
├── docs/                   # Documentation
├── tests/                  # Test suites
├── scripts/                # Build and dev scripts
├── config/                 # Configuration files
├── resources/              # Static resources
└── target/                 # Build output
```

## 3. Frontend Structure

```
src/frontend/
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── chat/          # Chat components
│   │   ├── command/       # Command palette
│   │   ├── settings/      # Settings panels
│   │   ├── permissions/   # Permission dialogs
│   │   └── common/        # Shared UI components
│   ├── hooks/             # React hooks
│   ├── stores/            # State management
│   ├── services/          # API client services
│   ├── types/             # TypeScript types
│   ├── utils/             # Utility functions
│   ├── styles/            # Global styles
│   └── App.tsx            # Root component
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── vite.config.ts
```

## 4. Backend Structure

```
src/backend/
├── aios/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py        # Pydantic settings
│   │   └── defaults.py         # Default configuration
│   ├── core/                   # Core modules
│   │   ├── __init__.py
│   │   ├── event_bus.py        # Event Bus implementation
│   │   ├── ai_router.py        # AI provider routing
│   │   ├── planner.py          # Task planning
│   │   ├── tool_manager.py     # Tool registration & execution
│   │   ├── permission_manager.py
│   │   ├── memory_system.py    # Memory management
│   │   ├── context_engine.py   # Context tracking
│   │   └── conversation.py     # Conversation management
│   ├── adapters/               # OS abstraction
│   │   ├── __init__.py
│   │   ├── windows_adapter.py  # Windows-specific implementation
│   │   └── base_adapter.py     # Abstract base class
│   ├── tools/                  # Built-in tools
│   │   ├── __init__.py
│   │   ├── file_operations.py
│   │   ├── system_info.py
│   │   ├── process_manager.py
│   │   ├── clipboard.py
│   │   └── browser.py
│   ├── vision/                 # Vision system
│   │   ├── __init__.py
│   │   ├── screenshot.py
│   │   ├── ocr.py
│   │   └── ui_understanding.py
│   ├── plugins/                # Plugin system
│   │   ├── __init__.py
│   │   ├── plugin_manager.py
│   │   └── sandbox.py
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   ├── conversation.py
│   │   ├── tool.py
│   │   ├── permission.py
│   │   ├── memory.py
│   │   └── events.py
│   ├── db/                     # Database
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── migrations/
│   │   └── models.py
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── tools.py
│   │   ├── settings.py
│   │   └── plugins.py
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── logger.py
│       ├── config.py
│       └── encryption.py
```

## 4. Configuration

```
config/
├── default.yaml           # Default configuration
├── development.yaml        # Development overrides
├── production.yaml         # Production overrides
└── schema.yaml            # Configuration schema
```

## 5. Tests

```
tests/
├── unit/                   # Unit tests
│   ├── test_event_bus.py
│   ├── test_ai_router.py
│   ├── test_planner.py
│   ├── test_tool_manager.py
│   ├── test_permission_manager.py
│   ├── test_memory_system.py
│   └── test_context_engine.py
├── integration/            # Integration tests
│   ├── test_conversation_flow.py
│   ├── test_tool_execution.py
│   └── test_plugin_system.py
├── e2e/                    # End-to-end tests
│   ├── test_basic_chat.py
│   └── test_workflow.py
├── fixtures/               # Test fixtures
└── conftest.py             # Pytest configuration
```

## 4. Scripts

```
scripts/
├── dev.sh                  # Start development environment
├── build.sh                # Build for production
├── test.sh                 # Run all tests
├── lint.sh                 # Run linters
├── format.sh               # Format code
├── seed.sh                 # Seed database with test data
└── setup.sh                # First-time setup
```

## 5. Resources

```
resources/
├── icons/                  # Application icons
├── sounds/                 # Notification sounds
├── fonts/                  # Custom fonts
└── locales/                # i18n translation files
```

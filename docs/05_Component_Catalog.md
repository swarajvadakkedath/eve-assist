# 05 — Component Catalog

> **Status:** Complete  
> **Scope:** All 80+ React components in `src/frontend/src/components/` and `src/frontend/src/memory/workspace/`  
> **Last Updated:** 2026-07-21

---

## 1. App Shell & Layout

### `AppShell` (`layout/AppShell.tsx`)
- **Purpose:** Root layout wrapper; places `sidebar` slot beside `children`
- **Props:** `sidebar: ReactNode`, `children: ReactNode`, `className?`
- **Dependencies:** None (pure div)
- **Accessibility:** Semantic via `pr-app-shell` class; role=none by default
- **State:** None (stateless container)

### `Sidebar` (`layout/Sidebar.tsx`)
- **Purpose:** Navigation sidebar with collapsible sections and nav items
- **Props:** `sections: SidebarSection[]`, `activeId?`, `collapsed?`, `onNavigate?`, `header?`, `footer?`, `title?`, `onToggleCollapse?`
- **Children:** Renders `<button>` elements per nav item; uses `Badge` for counts
- **Accessibility:** `role="navigation"`, `aria-label="Main navigation"`, `role="menuitem"`, `aria-current="page"`
- **Events:** `onNavigate(id)` on item click
- **State Ownership:** `collapsed` is parent-controlled

### `SidebarItem` (`layout/SidebarItem.tsx`)
- **Purpose:** Individual sidebar navigation button with icon, label, badge
- **Props:** Extends `ButtonHTMLAttributes` + `icon`, `label`, `active?`, `badge?`, `badgeVariant?`, `collapsed?`
- **Accessibility:** `role="menuitem"`, `aria-current`, `aria-label`
- **Dependencies:** `Badge` from common

### `TopBar` / `WorkspaceHeader` (`layout/TopBar.tsx`, `layout/WorkspaceHeader.tsx`)
- **Purpose:** Top bar with title, status area, and controls slot
- **Props:** `title?`, `controls?: ReactNode`, `status?: ReactNode`
- **Accessibility:** `role="banner"`
- **Note:** `WorkspaceHeader` is a duplicate alias of `TopBar`

### `StatusBar` (`layout/StatusBar.tsx`)
- **Purpose:** Bottom status bar with left/right slots and item list with colored dots
- **Props:** `items?: StatusBarItem[]`, `left?: ReactNode`, `right?: ReactNode`
- **Accessibility:** `role="status"`, `aria-label="Application status"`

### `Panel` (`layout/Panel.tsx`)
- **Purpose:** Generic panel container with header/body/footer sections
- **Props:** `children`, `header?`, `footer?` (extends `HTMLAttributes`)
- **Dependencies:** None

### `Surface` (`layout/Surface.tsx`)
- **Purpose:** Visual surface container with variant-based styling
- **Variants:** `primary | secondary | elevated | floating | panel`
- **Props:** `children`, `variant?`

### `PageContainer` (`layout/PageContainer.tsx`)
- **Purpose:** Page-level content wrapper with optional full-width mode
- **Props:** `children`, `full?` (extends `HTMLAttributes`)
- **Accessibility:** `role="region"`

### `SplitPane` (`layout/SplitPane.tsx`)
- **Purpose:** Resizable split pane (horizontal/vertical) with mouse + keyboard drag
- **Props:** `children: [ReactNode, ReactNode]`, `direction?`, `defaultSize?`, `minSize?`, `maxSize?`
- **State:** `splitSize` (local), `dragging` (useRef)
- **Accessibility:** `role="group"`, gutter `role="separator"` with `aria-valuemin/max/now`, keyboard arrow support
- **Performance:** Uses `useState` + `useRef` for drag; `onMouseMove` on container

### `ResizableLayout` (`layout/ResizableLayout.tsx`)
- **Purpose:** Sidebar + workspace layout with draggable resize and collapse
- **Props:** `sidebar`, `children`, `defaultSidebarWidth?`, `minSidebarWidth?`, `maxSidebarWidth?`, `collapsed?`, `onCollapsedChange?`, `collapsible?`
- **State:** `sidebarWidth` (local), `dragging` (useRef)
- **Accessibility:** `role="group"`, resize handle `role="separator"`, keyboard arrows

### `Workspace` (`layout/Workspace.tsx`)
- **Purpose:** Workspace content area with loading, empty, header/footer states
- **Props:** `children`, `header?`, `footer?`, `loading?`, `empty?`, `emptyMessage?`

---

## 2. Common / UI Primitives

### `Badge` (`common/Badge.tsx`)
- **Purpose:** Inline status badge with variants
- **Props:** `children`, `variant?: default|success|warning|error|info`, `size?: sm|md`
- **Accessibility:** `role="status"`

### `Button` (`common/Button.tsx`)
- **Purpose:** Styled button with loading state, icon, variants, sizes
- **Props:** `variant?: primary|secondary|ghost|danger`, `size?: sm|md|lg`, `loading?`, `icon?`
- **Accessibility:** `aria-busy` when loading, disabled when loading
- **Performance:** `forwardRef` for ref forwarding

### `Card` (`common/Card.tsx`)
- **Purpose:** Container card with padding and variant options
- **Props:** `children`, `padding?: none|sm|md|lg`, `variant?: elevated|outlined|filled`

### `Icon` (`common/Icon.tsx`)
- **Purpose:** Sized icon wrapper with optional aria label
- **Props:** `children`, `size?` (px), `label?`
- **Accessibility:** `role="img"` when label provided, `aria-hidden` otherwise

### `Input` (`common/Input.tsx`)
- **Purpose:** Form input with label, error state, hint text
- **Props:** Extends `InputHTMLAttributes` + `label?`, `error?`, `hint?`
- **Accessibility:** Auto-generated `useId()` for label/error/hint linking, `aria-invalid`, `aria-describedby`, `role="alert"` for errors
- **Performance:** `forwardRef`

### `Typography` (`common/Typography.tsx`)
- **Purpose:** Typography component with variant-based semantic tags and color
- **Variants:** `h1-h6 | body | body-sm | caption | label`
- **Props:** `variant?`, `as?` (override element), `color?` (via CSS variable)
- **Performance:** Memoized style objects

---

## 3. Conversation

### `ConversationView` (`conversation/ConversationView.tsx`)
- **Purpose:** Main conversation controller; manages messages, streaming, session inspector
- **Props:** `sidebar?`, `state?` (controlled), `actions?` (controlled)
- **State:** `activeId`, `messages[]`, `streaming`, `streamingContent`, `statusMessage`, `loading`, `error`, `customEntries[]`, `inspectedSessionId`
- **Events:** `sendMessage` (direct fetch + SSE streaming), `cancelStream`, `retryLast`, `createConversation`, `selectConversation`, `deleteConversation`, `handleInspectSession`
- **Dependencies:** `ConversationTimeline`, `Composer`, `ExecutionInspector`, `session/` store, `ConversationEmptyState/LoadingState/ErrorState`
- **Performance:** SSE streaming via `ReadableStream` reader; debounced rebuild of session entries via `subscribe`
- **Accessibility:** N/A (screen manages focus on send/stream)

### `ConversationTimeline` (`conversation/ConversationTimeline.tsx`)
- **Purpose:** Scrollable message list with auto-scroll and render-slot pattern
- **Props:** `messages[]`, `streaming?`, `streamingContent?`, `loading?`, `empty?`, `error?`, `onRetry?`, `onNewConversation?`, `renderEmpty?`, `renderLoading?`, `renderError?`, `customEntries?`, `onInspectSession?`
- **Children:** `TimelineItem` for each entry
- **Accessibility:** `role="log"`, `aria-label="Conversation messages"`, `aria-live="polite"`
- **Performance:** `useEffect` auto-scroll on `messages`/`streamingContent` change

### `TimelineItem` (`conversation/TimelineItem.tsx`)
- **Purpose:** Polymorphic timeline entry renderer (messages, sessions, executions, errors, etc.)
- **Entry types:** `message | streaming | typing | divider | execution | session | error | attachment | memory | result | system`
- **Dependencies:** `UserMessage`, `AssistantMessage`, `SystemMessage`, `ExecutionCard`, `ExecutionSessionCard`
- **Accessibility:** `role="separator"` for dividers, `role="alert"` for errors

### `Composer` (`conversation/Composer.tsx`)
- **Purpose:** Auto-resizing textarea with send button, Enter to send, Shift+Enter for newline
- **Props:** `onSend`, `disabled?`, `placeholder?`
- **State:** `value` (local)
- **Accessibility:** `aria-label="Message input"`
- **Performance:** Auto-height via `scrollHeight` math (max 200px)

### `UserMessage` / `AssistantMessage` / `SystemMessage` (`conversation/`)
- **Purpose:** Role-specific message renderers
- **UserMessage:** Avatar (U) + content + timestamp
- **AssistantMessage:** Avatar (E) + streaming support + `MarkdownRenderer` + `TypingIndicator`
- **SystemMessage:** Simple content + timestamp (no avatar)
- **Dependencies:** `MessageAvatar`, `Timestamp`, `MarkdownRenderer`, `TypingIndicator`

### `MarkdownRenderer` (`conversation/MarkdownRenderer.tsx`)
- **Purpose:** Custom markdown parser supporting code blocks, inline formatting, lists, streaming cursor
- **Features:** Code block with language header + copy button, inline bold/italic/code/strikethrough/links, unordered/ordered lists, streaming cursor animation
- **Dependencies:** `CodeBlock`, `StreamingCursor`
- **Performance:** `useMemo` for code block parsing; `dangerouslySetInnerHTML` for inline HTML

### `CodeBlock` (`conversation/CodeBlock.tsx`)
- **Purpose:** Syntax-highlighted code block with copy-to-clipboard
- **Props:** `language`, `code`
- **State:** `copied` (local, 2s timeout)
- **Accessibility:** `aria-label` for copy button

### `MessageAvatar` (`conversation/MessageAvatar.tsx`)
- **Purpose:** Role-based avatar initial display (U/E/S)
- **Props:** `role: user|assistant|system`
- **Accessibility:** `aria-hidden="true"`

### `Timestamp` (`conversation/Timestamp.tsx`)
- **Purpose:** Formatted time display with optional token count
- **Props:** `timestamp: string` (ISO), `tokens?: number`

### `StreamingCursor` (`conversation/StreamingCursor.tsx`)
- **Purpose:** Blinking cursor for streaming content
- **Props:** `visible?`

### `TypingIndicator` (`conversation/TypingIndicator.tsx`)
- **Purpose:** Animated three-dot typing indicator
- **Props:** `visible?`
- **Accessibility:** `role="status"`, `aria-label="Assistant is typing"`

### `ConversationEmptyState` / `ConversationLoadingState` / `ConversationErrorState`
- **Purpose:** Empty/welcome screen with keyboard shortcuts list; skeleton loading; error with retry
- **Accessibility:** `role="alert"` for errors, `role="status"` for loading

### Types (`conversation/types.ts`)
- `Message`: `id, conversation_id, role, content, timestamp, tokens_used, attachments, tool_calls?, metadata`
- `ConversationState`: `activeId, messages[], streaming, streamingContent, statusMessage, loading, error`
- `ConversationActions`: `sendMessage, cancelStream, retryLast, createConversation, selectConversation, deleteConversation, renameConversation`

---

## 4. Chat (Legacy)

### `ChatWindow` (`chat/ChatWindow.tsx`)
- **Purpose:** Standalone chat UI with sidebar, SSE streaming, error/retry
- **Props:** None (self-contained)
- **State:** Full conversation lifecycle managed internally
- **Dependencies:** `ConversationSidebar`, `MarkdownRenderer` (chat/ version)
- **Note:** Older implementation; `ConversationView` is the preferred replacement

### `MessageInput` (`chat/MessageInput.tsx`)
- **Purpose:** Basic auto-resizing textarea + send button
- **Props:** `onSend`, `disabled`

### `MessageList` (`chat/MessageList.tsx`)
- **Purpose:** Simple message list with loading state
- **Props:** `messages[]`, `loading`

### `MarkdownRenderer` (`chat/MarkdownRenderer.tsx`)
- **Purpose:** Duplicate of conversation/MarkdownRenderer with same features

---

## 5. Activity Center

### `ActivityCenter` (`activity/ActivityCenter.tsx`)
- **Purpose:** Session activity feed with filtering, counts, empty state
- **Props:** `onSelectSession?`, `onClear?`
- **State:** `filter`, `sessions[]` (subscribed to `SessionStore`)
- **Dependencies:** `ActivityFilter`, `ActivityFeed`, `ActivityToolbar`, `ActivityEmptyState`, `getSessionStore()`
- **Performance:** `useMemo` for counts and filtered sessions

### `ActivityFeed` (`activity/ActivityFeed.tsx`)
- **Purpose:** Filtered list of `ActivityItem` components
- **Props:** `sessions[]`, `filter`, `onSelectSession?`
- **Performance:** `useMemo` for client-side filtering

### `ActivityItem` (`activity/ActivityItem.tsx`)
- **Purpose:** Single session row with badge, title, capability tags, duration, step count
- **Props:** `session`, `onSelect?`
- **Accessibility:** `role="listitem"`, `aria-label` with status

### `ActivityBadge` (`activity/ActivityBadge.tsx`)
- **Purpose:** Status badge with colored dot and label
- **Props:** `status`, `count?`
- **Statuses:** planning, running, waiting, permission, retrying, paused, completed, failed, cancelled, background
- **Accessibility:** `role="status"`

### `ActivityFilter` (`activity/ActivityFilter.tsx`)
- **Purpose:** Filter button group with counts
- **Props:** `active`, `onChange`, `counts`
- **Filters:** all, running, completed, failed, browser, memory, plugins, voice, vision, files
- **Accessibility:** `role="group"`, `aria-pressed`

### `ActivityToolbar` (`activity/ActivityToolbar.tsx`)
- **Purpose:** Session count + "Clear All" button
- **Props:** `totalCount`, `onClear?`

### `ActivityEmptyState` (`activity/ActivityEmptyState.tsx`)
- **Purpose:** Empty state with filter-aware messaging

### Types (`activity/types.ts`)
- `ActivityFilter`: Union type of all filter values
- `STATUS_GROUP`: Maps session statuses to filter groups
- `ACTIVITY_FILTERS`: Array of filter definitions with labels

---

## 6. Command System

### `CommandCenter` (`command/CommandCenter.tsx`)
- **Purpose:** Command palette modal orchestrating input, results, history, footer
- **Props:** `workspaces[]`, `onClose`, `onNavigate`, `onSwitchWorkspace?`, `activeWorkspaceId?`, `defaultQuery?`
- **State:** Via `useCommandStore` (external)
- **Events:** Arrow/Enter/Escape keyboard handling, selection, pin toggle, history clear
- **Accessibility:** `role="dialog"`, `aria-modal="true"`, `aria-label="Command palette"`
- **Dependencies:** `CommandInput`, `CommandResults`, `CommandHistory`, `CommandFooter`, `CommandStore`, `CommandRegistry`

### `useCommandPalette` (`command/CommandPalette.tsx`)
- **Purpose:** Hook that registers static commands, listens for Ctrl+K, returns `{open, setOpen, defaultQuery, openPalette, renderPalette}`
- **Props:** `workspaces[]`, `onNavigate`, `onSwitchWorkspace?`, `activeWorkspaceId?`

### `CommandInput` (`command/CommandInput.tsx`)
- **Purpose:** Search input with cmd icon, autoFocus, clear button
- **Props:** `value`, `onChange`, `onKeyDown`, `placeholder?`, `inputRef`
- **Accessibility:** `aria-label="Command search"`, `autoComplete="off"`

### `CommandResults` (`command/CommandResults.tsx`)
- **Purpose:** Grouped command results with selection highlighting
- **Props:** `groups[]`, `selectedIndex`, `onSelect`, `onHover`, `loading`, `error`, `query`
- **Children:** `CommandCategory`, `CommandItemRow`
- **Accessibility:** `role="listbox"`
- **Performance:** `useMemo` for flat index mapping

### `CommandCategory` (`command/CommandCategory.tsx`)
- **Purpose:** Category group header with item count
- **Props:** `label`, `count?`

### `CommandItemRow` (`command/CommandItemRow.tsx`)
- **Purpose:** Single command row with icon, name, description, shortcut
- **Props:** `item`, `selected`, `onSelect`, `onHover`
- **Accessibility:** `role="option"`, `aria-selected`

### `CommandShortcut` (`command/CommandShortcut.tsx`)
- **Purpose:** Renders keyboard shortcut with symbol mapping (⌘, ⌃, ⌥, ⇧)
- **Props:** `shortcut` (e.g. "Mod+K")

### `CommandHistory` (`command/CommandHistory.tsx`)
- **Purpose:** Recent commands list with pin/unpin and clear
- **Props:** `entries[]`, `pinnedIds[]`, `onSelect`, `onTogglePin`, `onClear`, `allCommands`
- **Accessibility:** `role="region"`, `aria-label="Recent commands"`

### `CommandSuggestions` (`command/CommandSuggestions.tsx`)
- **Purpose:** Suggestion list for contextual command recommendations
- **Props:** `suggestions[]`, `onSelect`

### `CommandPreview` (`command/CommandPreview.tsx`)
- **Purpose:** Detail panel for selected command
- **Props:** `data: CommandPreviewData | null`

### `CommandFooter` (`command/CommandFooter.tsx`)
- **Purpose:** Footer with navigation tips and result count
- **Props:** `totalResults`, `selectedIndex`, `hasQuery`
- **Accessibility:** `role="toolbar"`

### `CommandEmptyState` / `CommandLoadingState` / `CommandErrorState`
- **Purpose:** Empty, loading, and error states for command results
- **Accessibility:** `role="alert"` for errors, `role="status"` for loading

### `NaturalLanguageResult` (`command/NaturalLanguageResult.tsx`)
- **Purpose:** Displays NL interpretation with confidence and execute button
- **Props:** `intent`, `onExecute`

### `CommandStore` (`command/CommandStore.ts`)
- **Purpose:** Singleton store managing query, results, selection, history, pins
- **Features:** Debounced search (150ms), localStorage persistence, subscription model
- **Methods:** `setQuery`, `selectNext/Previous`, `getSelectedItem`, `recordExecution`, `togglePin`, `clearHistory`, `getRecentCommands`, `reset`

### `CommandRegistry` (`command/CommandRegistry.ts`)
- **Purpose:** Registry for static commands and dynamic providers with fuzzy search
- **Features:** Provider registration, static commands management, `fuzzyMatch` + scoring, category ordering

### `useCommandStore` (`command/useCommandStore.ts`)
- **Purpose:** React hook using `useSyncExternalStore` for reactivity

### Types (`command/types.ts`)
- `CommandItem`: `id, name, description, category, resultType, icon?, shortcut?, keywords?, payload?, action, highlight?`
- `CommandProvider`: `id, name, commands[], search(), refresh?()`
- `CommandStoreState`: `query, results[], groups[], selectedIndex, loading, error, recentCommands[], pinnedCommands[]`
- `CommandCategory`: Union of 14 categories
- `CommandResultType`: Union of 10 result types

---

## 7. Execution

### Directory structure: `execution/`
- `ExecutionCard.tsx`, `ExecutionBadge.tsx`, `ExecutionDuration.tsx`, `ExecutionProgress.tsx`
- `ExecutionHeader.tsx`, `ExecutionFooter.tsx`, `ExecutionSummary.tsx`, `ExecutionResult.tsx`
- `ExecutionActions.tsx`, `ExecutionNode.tsx`, `ExecutionThread.tsx`, `ExecutionLogs.tsx`
- `ExecutionMetadata.tsx`, `ExecutionPanel.tsx`, `ExecutionLoadingState.tsx`
- `ExecutionEmptyState.tsx`, `ExecutionErrorState.tsx`
- `PermissionCard.tsx`, `RecoveryCard.tsx`
- `nodeConfig.ts`, `types.ts`, `index.ts`
- `session/` — session-based execution store with event sourcing

### `ExecutionCard` (`execution/ExecutionCard.tsx`)
- **Purpose:** Card display for an execution state
- **Props:** `execution: ExecutionState`

### `ExecutionSessionCard` (`execution/session/ExecutionSessionCard.tsx`)
- **Purpose:** Card display for an execution session with inspect action
- **Props:** `session: ExecutionSession`, `onInspect?`

### Key patterns:
- Event-sourced session store (`session/`)
- `adaptBackendEvent` for SSE-to-session event translation
- `createCompletedEvent` for session finalization
- Status-based step rendering with capability grouping

---

## 8. Inspector

### `ExecutionInspector` (`inspector/ExecutionInspector.tsx`)
- **Purpose:** Modal dialog for inspecting execution sessions across 9 tabs
- **Props:** `sessionId`, `onClose`
- **State:** `activeTab`, `session` (subscribed to `SessionStore`)
- **Accessibility:** `role="dialog"`, `aria-modal="true"`, Escape to close
- **Dependencies:** All 9 inspector tab components

### Tab Components:

| Tab | Component | Purpose |
|-----|-----------|---------|
| Summary | `InspectorSummary` | Title, status, duration, tools, capabilities, result, error |
| Timeline | `InspectorTimeline` | Step-by-step execution graph |
| Logs | `InspectorLogs` | Filterable log entries with copy |
| Tools | `InspectorTools` | List of executed tools with status/duration |
| Files | `InspectorFiles` | Created/read/modified/deleted file counts |
| Permissions | `InspectorPermissions` | Permission request count and status |
| Performance | `InspectorPerformance` | Duration bar charts per step |
| Metadata | `InspectorMetadata` | All session metadata fields |
| Raw Event | `InspectorJsonView` | Raw JSON with collapsible display and copy |

### `InspectorSummary`
- **Props:** `session`
- **Features:** Status badge, start/finish/duration grid, tools count, capabilities, files changed, result outcome, error display

### `InspectorTimeline`
- **Purpose:** Vertical flow from Request → Steps → Result
- **Features:** Status-colored step icons, duration, error display, connector lines

### `InspectorLogs`
- **Props:** `session`
- **Features:** Collapsible log list, level filter (all/info/warn/error/debug), copy to clipboard, scrollable (max 400px)

### `InspectorTools`
- **Props:** `session`
- **Features:** Tool cards with status indicator, capability tag, duration, error

### `InspectorFiles`
- **Props:** `session`
- **Features:** File operation groups (created/read/modified/deleted) with counts, step list filtered to file operations

### `InspectorPermissions`
- **Props:** `session`
- **Features:** Permission request count, resolution status display

### `InspectorPerformance`
- **Props:** `session`
- **Features:** Bar chart for total duration, steps total, longest step, per-step timing

### `InspectorMetadata`
- **Props:** `session`
- **Features:** Key-value grid of all session metadata fields

### `InspectorJsonView`
- **Props:** `session`
- **Features:** Collapsible raw JSON view with copy button

### `InspectorActions`
- **Props:** `session`, `onClose`
- **Features:** Copy summary, open result (future), close inspector

### `InspectorTabs`
- **Props:** `active`, `onChange`
- **Accessibility:** `role="tablist"`, `role="tab"`, `aria-selected`

### Types (`inspector/types.ts`)
- `InspectorTab`: `summary | timeline | logs | tools | files | permissions | performance | metadata | raw`
- `INSPECTOR_TABS`: Array of tab definitions with labels

---

## 9. Voice

### `VoiceButton` (`voice/VoiceButton.tsx`)
- **Purpose:** Microphone button with push-to-talk, audio level ring, tooltip
- **Props:** `onTranscript?`, `onStateChange?`, `pushToTalkKey?` (default "v")
- **State:** `isListening`, `isSpeaking`, `audioLevel`, `showTooltip`
- **Events:** Toggle listening via `voiceService.connect/startListening/stopListening`; push-to-talk via keydown/keyup
- **Dependencies:** `voiceService`
- **Accessibility:** SVG mic icon, tooltip with state text

### `VoiceIndicator` (`voice/VoiceIndicator.tsx`)
- **Purpose:** Voice state indicator dot with pulsing animation
- **Props:** `compact?` (shows dot only)
- **State:** `isListening`, `isSpeaking`, `state`
- **Accessibility:** Hidden when idle, colored dot + label

### `InterruptButton` (`voice/InterruptButton.tsx`)
- **Purpose:** Stop button shown when Eve is speaking; triggers `voiceService.bargeIn()`
- **Dependencies:** `voiceService`
- **Accessibility:** Hidden when not speaking, `title="Interrupt Eve"`

### `TranscriptPanel` (`voice/TranscriptPanel.tsx`)
- **Purpose:** Real-time voice transcript display with partial + final items
- **Props:** `maxItems?` (default 50), `compact?`
- **State:** `transcripts[]`, `partialText`
- **Performance:** Auto-scroll to bottom; slice to maxItems

### `AudioLevelMeter` (`voice/AudioLevelMeter.tsx`)
- **Purpose:** Visual audio level bar display during listening
- **Props:** `barCount?`, `height?`, `width?`
- **State:** `level`, `active`; uses `requestAnimationFrame` for smooth animation
- **Dependencies:** `voiceService`

### `VoiceSettingsPanel` (`voice/VoiceSettingsPanel.tsx`)
- **Purpose:** Voice configuration form (STT/TTS provider, devices, language, voice, rate, pitch, push-to-talk key, wake word, continuous listening)
- **Props:** `onClose?`
- **State:** `config`, `inputDevices[]`, `outputDevices[]`, `voices[]`, `saving`
- **Dependencies:** `voiceService.fetchConfig/fetchInputDevices/fetchOutputDevices/fetchVoices/updateConfig`

---

## 10. Vision

### `ScreenCaptureButton` (`vision/ScreenCaptureButton.tsx`)
- **Purpose:** Button to capture full screen via `api.vision.capture()`
- **Props:** `onCapture?`, `onError?`
- **State:** `capturing` (local)

### `ObservationPanel` (`vision/ObservationPanel.tsx`)
- **Purpose:** Screen observation panel with summary, stats, OCR text, UI elements, layout regions
- **Props:** `onClose?`
- **State:** `observation`, `loading`, `error`, `expanded` (collapsible sections)
- **Dependencies:** `api.vision.analyze()`
- **Accessibility:** Escape to close

### `LivePreview` (`vision/LivePreview.tsx`)
- **Purpose:** Cyclical screen capture preview with start/stop
- **Props:** `interval?` (default 2000ms), `autoStart?`, `onClose?`
- **State:** `active`, `imageUrl`, `error`
- **Performance:** `setInterval` for capture loop

### `ImageUpload` (`vision/ImageUpload.tsx`)
- **Purpose:** Drag-and-drop image upload zone with validation (type, size ≤ 10MB)
- **Props:** `onImageSelected`, `onError?`
- **State:** `dragOver` (local)

### `RegionSelectionOverlay` (`vision/RegionSelectionOverlay.tsx`)
- **Purpose:** Mouse-drag region selector overlay on image
- **Props:** `onRegionSelected`, `onCancel`, `imageUrl?`
- **State:** `start`, `current`, `selecting`
- **Accessibility:** Escape to cancel, minimum 10×10 region

### `VisionSettings` (`vision/VisionSettings.tsx`)
- **Purpose:** Vision configuration form (provider, OCR engine, capture quality, privacy filters, auto-redact, observation mode, monitor selection)
- **Dependencies:** `api.vision.config()/providers()/monitors()/updateConfig()`

---

## 11. Desktop / Shell

### `App` (`App.tsx`)
- **Purpose:** Root application component; orchestrates all top-level panels
- **State:** `theme`, `activeWorkspace`, `settingsOpen`, `pluginsOpen`, `toolsOpen`, `currentConversationId`, `visionOpen`, `visionMode`
- **Events:** Global keyboard shortcuts (Ctrl+,/P/T/M/I), `handleNavigate` dispatch to custom events (`aios:*`)
- **Children:** `StatusIndicator`, `VoiceIndicator`, `InterruptButton`, `TranscriptPanel`, `ScreenCaptureButton`, `VoiceButton`, `NotificationCenter`, `WorkspaceRegistry`, `CommandPalette`, `SettingsPanel`, `ToolCenterPanel`, `PluginManagerPanel`, `ObservationPanel`/`LivePreview`/`ImageUpload` (conditional)
- **Dependencies:** `useCommandPalette`, `voiceService`, `api`

### `StatusIndicator` (`desktop/StatusIndicator.tsx`)
- **Purpose:** Polling status indicator (2s interval) showing app state
- **States:** starting, ready, listening, thinking, planning, executing, waiting, updating, offline, error
- **Dependencies:** `fetch("/api/v1/desktop/status")`

### `SettingsPanel` (`desktop/SettingsPanel.tsx`)
- **Purpose:** Multi-tab settings panel (general/voice/vision/ai/shortcuts/notifications/startup/privacy)
- **Props:** `onClose`
- **State:** `settings`, `loading`, `saving`, `activeTab`
- **Dependencies:** `VoiceSettingsPanel`, `VisionSettings`
- **Accessibility:** Overlay with click-outside-to-close

### `NotificationCenter` (`desktop/NotificationCenter.tsx`)
- **Purpose:** Notification bell with dropdown panel and clear history
- **State:** `notifications[]`, `open`, `unread`
- **Dependencies:** `fetch("/api/v1/desktop/notifications/history")`
- **Accessibility:** Click-outside-to-close

### `CommandPalette` (`desktop/CommandPalette.tsx`) (legacy)
- **Purpose:** Older command palette (superseded by command/CommandCenter)
- **Props:** `onClose`, `onNavigate`

---

## 12. Workspace

### `WorkspaceRegistry` (`workspace/WorkspaceRegistry.tsx`)
- **Purpose:** Renders active workspace component by ID
- **Props:** `workspaces: WorkspaceDefinition[]`, `activeId`, `fallback?`
- **Children:** Delegates to registered workspace component

### `WorkspacePanel` (`workspace/WorkspacePanel.tsx`)
- **Purpose:** Workspace dashboard showing projects, git status, editors, applications, terminals (5s polling)
- **Dependencies:** Multiple `/api/v1/workspace/*` endpoints
- **State:** `workspace`, `projects[]`, `repos[]`, `editors[]`, `apps[]`, `terminals[]`, `loading`, `expanded`

---

## 13. Sidebar

### `ConversationSidebar` (`sidebar/ConversationSidebar.tsx`)
- **Purpose:** Conversation list sidebar with search, rename, delete, new conversation
- **Props:** `activeId`, `onSelect`, `onNew`, `onDelete`, `onRename`
- **State:** `conversations[]`, `search`, `loading`, `renamingId`, `renameValue`
- **Accessibility:** Double-click to rename, confirm on delete

---

## 14. Permissions

### `PermissionDialog` (`permissions/PermissionDialog.tsx`)
- **Purpose:** Modal dialog for tool permission requests
- **Props:** `request` (id, tool_id, level, description), `onGrant`, `onDeny`
- **Accessibility:** Level badge (0-4) with human-readable risk label

---

## 15. Plugins

### `PluginManagerPanel` (`plugins/PluginManagerPanel.tsx`)
- **Purpose:** Full plugin management UI with list/detail views, search, enable/disable/reload/remove
- **Props:** `onClose`
- **State:** `plugins[]`, `loading`, `error`, `search`, `view`, `selectedPlugin`, `healthSummary`, `actionLoading`
- **Dependencies:** `api.plugins.list()/get()/enable()/disable()/reload()/remove()/health()`
- **Features:** Plugin cards with status dot, detail view with health stats, capabilities, dependencies, tags, license
- **Accessibility:** Overlay pattern, status colors for accessibility

---

## 16. Tools

### `ToolCenterPanel` (`tools/ToolCenterPanel.tsx`)
- **Purpose:** Tool browsing and execution center with category grouping, search, permission filtering
- **Props:** `onClose`
- **State:** `categories{}`, `totalTools`, `loading`, `error`, `expandedCat`, `searchQuery`, `filterPermission`, `executeResult`, `executing`, `commands{}`, `commandInputs{}`, `contentInputs{}`
- **Dependencies:** `api.tools.list()/execute()`
- **Features:** Terminal command execution with output display, content tool inputs (path/query/source), network tool inputs (URL/hostname/token/headers), permission level badges, capability badges, parameter details

---

## 17. Memory Workspace

### `MemoryWorkspace` (`memory/workspace/MemoryWorkspace.tsx`)
- **Purpose:** Main memory workspace with sidebar navigation, explorer, search, and inspector
- **Props:** `sections?`, `defaultView?`, `showInspector?`
- **State:** `activeView`, `searchQuery`, `selectedNode`, `showSearch`
- **Dependencies:** `MemorySidebar`, `MemoryExplorer`, `MemoryInspector`, `MemorySearch`, `getMemoryStore()`
- **Layout:** Sidebar | Content | Inspector (when node selected)

### `MemorySidebar` (`memory/workspace/MemorySidebar.tsx`)
- **Purpose:** Navigation sidebar with section list and search input
- **Props:** `sections[]`, `activeSection`, `onSectionChange`, `onSearch?`, `searchQuery?`
- **Sections:** recent, pinned, explorer, knowledge, artifacts, people, browser, voice, vision, collections, tags, timeline
- **Accessibility:** `aria-label="Memory navigation"`, `role="button"` on items, keyboard Enter/Space

### `MemoryExplorer` (`memory/workspace/MemoryExplorer.tsx`)
- **Purpose:** Content area with toolbar, breadcrumbs, filters, and grid/list/timeline views
- **Props:** `view`, `searchQuery?`, `onSelect?`, `selectedNodeId?`
- **State:** `viewMode`, `sortField`, `sortOrder`, `showFilters`, `filters`
- **Dependencies:** `MemoryToolbar`, `MemoryBreadcrumbs`, `MemoryFilters`, `MemoryGrid`, `MemoryList`, `MemoryTimeline`
- **Performance:** `useMemo` for filtered/sorted node computation

### `MemoryInspector` (`memory/workspace/MemoryInspector.tsx`)
- **Purpose:** Node detail panel with preview, importance/confidence bars, metadata, neighbors, edges
- **Props:** `node`, `onClose?`, `actions?`
- **Dependencies:** `MemoryPreview`, `MemoryActions`, `getMemoryStore()`
- **Accessibility:** `role="complementary"`, `aria-label="Node inspector"`, progress bars with `role="progressbar"`

### `MemorySearch` (`memory/workspace/MemorySearch.tsx`)
- **Purpose:** Full-text search with debounced input and result list
- **Props:** `onSelect?`, `onClose?`, `placeholder?`
- **State:** `query`, `results`, `loading`
- **Dependencies:** `MemoryList`, `getMemoryStore().query.execute()`
- **Performance:** 200ms debounce on input

### `MemoryToolbar` (`memory/workspace/MemoryToolbar.tsx`)
- **Purpose:** Toolbar with view toggle (grid/list), sort controls, filter toggle, count, new node button
- **Props:** `viewMode`, `onViewModeChange`, `sortField`, `sortOrder`, `onSortChange`, `onNewNode?`, `totalCount`, `showFilters?`, `onToggleFilters?`
- **Accessibility:** `role="toolbar"`, `aria-pressed` for toggles

### `MemoryFilters` (`memory/workspace/MemoryFilters.tsx`)
- **Purpose:** Filter panel by super type, status, tags, pinned state
- **Props:** `filters`, `onChange`, `availableTags[]`
- **Accessibility:** `role="region"`, `aria-label="Filters"`, `fieldset`/`legend` for groups, `aria-pressed` on toggle buttons

### `MemoryBreadcrumbs` (`memory/workspace/MemoryBreadcrumbs.tsx`)
- **Purpose:** Breadcrumb navigation trail
- **Props:** `items[]`, `onNavigate?`
- **Accessibility:** `nav` with `aria-label="Breadcrumb"`, `aria-current="page"` on last item

### `MemoryGrid` (`memory/workspace/MemoryGrid.tsx`)
- **Purpose:** Grid layout of `MemoryCard` components
- **Props:** `nodes[]`, `selectedId?`, `onSelect?`, `emptyMessage?`
- **Accessibility:** `role="list"`, `aria-label="Memory items grid"`

### `MemoryList` (`memory/workspace/MemoryList.tsx`)
- **Purpose:** List layout of memory nodes with type badge, title, relative timestamp
- **Props:** `nodes[]`, `selectedId?`, `onSelect?`, `emptyMessage?`
- **Accessibility:** `role="list"`, `role="listitem"`, `aria-selected`, keyboard Enter/Space

### `MemoryCard` (`memory/workspace/MemoryCard.tsx`)
- **Purpose:** Individual memory node card with header (badge + pin), title, summary, tags, timestamp
- **Props:** `node`, `selected?`, `showTags?`, `showMeta?`, `compact?`
- **Accessibility:** `role="button"`, `tabIndex={0}`, `aria-selected`, `aria-labelledby`

### `MemoryPreview` (`memory/workspace/MemoryPreview.tsx`)
- **Purpose:** Read-only preview of memory node metadata and content
- **Props:** `node`
- **Features:** Title, type, source, timestamps, status, pin/archive/verified flags, summary, tags

### `MemoryActions` (`memory/workspace/MemoryActions.tsx`)
- **Purpose:** Action toolbar for memory node (pin, edit, archive, delete)
- **Props:** `node`, `onPin?`, `onArchive?`, `onDelete?`, `onEdit?`
- **Accessibility:** `role="toolbar"`, `aria-label="Node actions"`

### `MemoryTimeline` (`memory/workspace/MemoryTimeline.tsx`)
- **Purpose:** Time-grouped timeline view (Today/Yesterday/This Week/etc.)
- **Props:** `nodes[]`, `onSelect?`, `emptyMessage?`
- **Features:** Automatic grouping by recency, count per group, relative timestamps
- **Accessibility:** `role="list"`, `role="heading"` for group headers

### `useMemoryStore` (`memory/workspace/useMemoryStore.ts`)
- **Purpose:** React hooks for memory store reactivity (`useMemoryStore`, `useMemoryEvent`, `useMemoryNodes`)

---

## 18. Component Dependency Graph

```
App.tsx
├── StatusIndicator (desktop)
├── VoiceIndicator (voice)
├── InterruptButton (voice)
├── TranscriptPanel (voice)
├── ScreenCaptureButton (vision)
├── VoiceButton (voice)
├── NotificationCenter (desktop)
├── WorkspaceRegistry (workspace)
│   ├── ConversationView (conversation)
│   │   ├── ConversationTimeline
│   │   │   └── TimelineItem
│   │   │       ├── UserMessage
│   │   │       ├── AssistantMessage
│   │   │       │   └── MarkdownRenderer
│   │   │       │       ├── CodeBlock
│   │   │       │       └── StreamingCursor
│   │   │       ├── SystemMessage
│   │   │       ├── ExecutionCard (execution)
│   │   │       └── ExecutionSessionCard (execution/session)
│   │   ├── Composer
│   │   └── ExecutionInspector (inspector)
│   │       ├── InspectorTabs
│   │       ├── InspectorSummary/Timeline/Logs/Tools/Files
│   │       ├── InspectorPermissions/Performance/Metadata
│   │       └── InspectorJsonView/Actions
│   └── ActivityCenter (activity)
│       ├── ActivityToolbar
│       ├── ActivityFilter
│       ├── ActivityFeed → ActivityItem → ActivityBadge
│       └── ActivityEmptyState
├── CommandPalette (via useCommandPalette)
│   └── CommandCenter
│       ├── CommandInput
│       ├── CommandResults → CommandCategory + CommandItemRow
│       ├── CommandHistory → CommandItemRow
│       ├── CommandFooter
│       └── CommandStore + CommandRegistry
├── SettingsPanel (desktop)
│   ├── VoiceSettingsPanel (voice)
│   └── VisionSettings (vision)
├── ToolCenterPanel (tools)
├── PluginManagerPanel (plugins)
├── ObservationPanel (vision)
├── LivePreview (vision)
└── ImageUpload (vision)

MemoryWorkspace (memory/workspace)
├── MemorySidebar
├── MemoryExplorer
│   ├── MemoryToolbar
│   ├── MemoryBreadcrumbs
│   ├── MemoryFilters
│   ├── MemoryGrid → MemoryCard
│   ├── MemoryList
│   └── MemoryTimeline
├── MemoryInspector
│   ├── MemoryPreview
│   └── MemoryActions
└── MemorySearch → MemoryList
```

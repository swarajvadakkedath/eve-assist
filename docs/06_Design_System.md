# 06 — Eve Design System

> **Status:** Approved · v2.0.0  
> **Scope:** Official design tokens, component patterns, and visual language for Eve OS  
> **Last Updated:** 2026-07-21  
> **Design Tokens Source:** `src/frontend/src/styles/tokens.css`, `globals.css`, `primitives.css`

---

## 1. Design Philosophy

Eve OS follows five core principles:

- **Invisible when idle** — The interface recedes, letting content and tasks take focus. UI chrome is minimal and contextual.
- **Clear communication** — Every system action is explained in plain language. No silent failures or mysterious loading states.
- **Progressive disclosure** — Novice users see simplicity; power users reveal depth on demand. Complexity is never forced.
- **Consistent patterns** — The same interaction model applies across chat, execution, memory, settings, and tools. Learn once, use everywhere.
- **Accessible by default** — WCAG 2.2 AA compliance is baked into the token system, not bolted on after the fact.

---

## 2. Color System

### 2.1 Theme Tokens

Eve OS uses CSS custom properties scoped to `:root` (dark) and `.light` (light). All component colors derive from these 9 base tokens.

| Token | Dark | Light | Purpose |
|-------|------|-------|---------|
| `--bg-primary` | `#1a1a2e` | `#ffffff` | Main application background |
| `--bg-secondary` | `#16213e` | `#f5f5f5` | Sidebar, cards, panels |
| `--bg-tertiary` | `#0f3460` | `#e8e8e8` | Elevated surfaces, hover states |
| `--text-primary` | `#e0e0e0` | `#1a1a2e` | Body text, headings |
| `--text-secondary` | `#a0a0a0` | `#666666` | Secondary text, labels, metadata |
| `--accent` | `#7c73ff` | `#6c63ff` | Primary interactive color |
| `--accent-hover` | `#6c63ff` | `#5b52e0` | Accent hover state |
| `--success` | `#66bb6a` | `#4caf50` | Success states, completed |
| `--warning` | `#ffb74d` | `#ff9800` | Warning states, waiting |
| `--error` | `#ef5350` | `#f44336` | Error states, failed |
| `--border` | `#2a2a4a` | `#e0e0e0` | Borders, dividers, outlines |

### 2.2 Semantic Color Tokens

Derived from base tokens for contextual usage:

```css
--color-text-primary: var(--text-primary);
--color-text-secondary: var(--text-secondary);
--color-text-muted: color-mix(in srgb, var(--text-primary) 50%, transparent);
--color-border: var(--border);
--color-border-hover: color-mix(in srgb, var(--accent) 40%, var(--border));
--color-border-active: var(--accent);
--color-accent: var(--accent);
--color-success: var(--success);
--color-warning: var(--warning);
--color-error: var(--error);
```

### 2.3 Surface Tokens

| Token | Maps To | Usage |
|-------|---------|-------|
| `--surface-primary` | `--bg-primary` | Main content area |
| `--surface-secondary` | `--bg-secondary` | Sidebar, panels |
| `--surface-sidebar` | `--bg-secondary` | Navigation sidebar |
| `--surface-floating` | `--bg-secondary` | Dropdowns, tooltips |
| `--surface-overlay` | `rgba(0,0,0,0.5)` | Modal backdrops |
| `--surface-elevated` | `--bg-tertiary` | Hover, active items |
| `--surface-panel` | `--bg-primary` | Panel body |

### 2.4 Execution State Colors

```css
--execution-running:  #3b82f6;
--execution-completed: var(--success);
--execution-failed:   var(--error);
--execution-waiting:  var(--warning);
--execution-permission: #a855f7;
```

---

## 3. Typography

### 3.1 Font Family

```css
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
```

- **Inter** at weights 400, 500, 600, 700 for all UI text
- **JetBrains Mono** for code blocks, inline code, logs, terminal output

### 3.2 Type Scale

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `--text-xs` | 11px | 400 | 1.5 | Captions, metadata, timestamps |
| `--text-sm` | 12px | 500 | 1.5 | Labels, secondary text, buttons |
| `--text-base` | 14px | 400 | 1.75 | Body text, paragraphs |
| `--text-lg` | 16px | 600 | 1.5 | Subheadings, message headers |
| `--text-xl` | 20px | 600 | 1.25 | Section headings |
| `--text-2xl` | 24px | 700 | 1.25 | Page titles, welcome screen |
| `--text-3xl` | 32px | 700 | 1.25 | Hero display text |

### 3.3 Line Heights

```css
--leading-none:    1;
--leading-tight:   1.25;
--leading-normal:  1.5;
--leading-relaxed: 1.75;
```

### 3.4 Typography Usage Guidelines

| Element | Variant | Font | Weight | Size |
|---------|---------|------|--------|------|
| Page title | h1 | Inter | 700 | 24px (`--text-2xl`) |
| Section heading | h2 | Inter | 600 | 20px (`--text-xl`) |
| Card title | h3 | Inter | 600 | 16px (`--text-lg`) |
| Subheading | h4 | Inter | 600 | 14px (`--text-base`) |
| Label | h5 | Inter | 500 | 14px (`--text-base`) |
| Small label | h6 | Inter | 500 | 12px (`--text-sm`) |
| Body text | body | Inter | 400 | 14px (`--text-base`) |
| Small body | body-sm | Inter | 400 | 12px (`--text-sm`) |
| Caption | caption | Inter | 400 | 11px (`--text-xs`) |
| Inline code | code | JetBrains Mono | 400 | 13px |
| Code blocks | pre | JetBrains Mono | 400 | 13px |

---

## 4. Spacing System

### 4.1 Spacing Scale

Based on a 4px grid, the spacing scale is:

```css
--space-1:  4px;
--space-2:  8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  20px;
--space-6:  24px;
--space-8:  32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
```

### 4.2 Spacing Rules

| Context | Padding | Gap |
|---------|---------|-----|
| Page content | `--space-6` | — |
| Card body | `--space-4` | `--space-3` |
| Panel body | `--space-4` | `--space-3` |
| Sidebar items | `--space-2` `--space-3` | `--space-2` |
| Message items | `--space-2` 0 | `--space-3` |
| Button icons | `--space-1` `--space-3` | `--space-2` |
| Form groups | — | `--space-1` |
| Modal padding | `--space-5` | `--space-4` |
| Toolbar | — | `--space-2` |

---

## 5. Layout

### 5.1 App Shell

```
┌─────────────────────────────────────┐
│  App Header (--topbar-height: 40px)  │
├────────┬────────────────────────────┤
│        │                            │
│ Sidebar│    Content (flex: 1)        │
│ 260px  │                            │
│        │                            │
├────────┴────────────────────────────┤
│  Status Bar (--statusbar-height: 28px) │
└─────────────────────────────────────┘
```

- **Sidebar:** `--sidebar-width: 260px` expanded, `--sidebar-collapsed-width: 52px`
- **Sidebar min/max:** `200px` / `400px` (resizable)
- **TopBar height:** `40px`
- **StatusBar height:** `28px`

### 5.2 Breakpoint Strategy

No fixed breakpoints. Layout adapts via:
- Collapsible sidebar (toggle at narrow widths)
- Content `min-width: 0` with `overflow: hidden`
- Message timeline constrained to `max-width: 800px` and centered
- Panels and modals centered with fixed max-width + `max-height: 80vh`

### 5.3 Layout Components

| Component | Flex Direction | Overflow | Sizing |
|-----------|---------------|----------|--------|
| `AppShell` | row | hidden | 100vw x 100vh |
| `Sidebar` | column | hidden | Fixed width, full height |
| `Workspace` | column | hidden | flex: 1, full height |
| `SplitPane` | row / column | hidden | flex: 1 |
| `PageContainer` | column | auto (y) | flex: 1, padding |

---

## 6. Elevation & Shadows

### 6.1 Shadow Tokens

```css
/* Dark theme */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.3);
--shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.3);

/* Light theme overrides */
.light {
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.12);
}
```

### 6.2 Elevation Levels

| Level | Shadow | Z-Index | Usage |
|-------|--------|---------|-------|
| Flat | none | auto | Surface, cards |
| Raised | `--shadow-sm` | auto | Hover states, sidebar items |
| Overlay | `--shadow-md` | `--z-dropdown: 100` | Dropdowns, tooltips, command palette |
| Modal | `--shadow-lg` | `--z-modal: 1100` | Settings, plugins, dialogs |
| Backdrop | none | `--z-overlay: 1000` | Semi-transparent overlay |

---

## 7. Border Radius

### 7.1 Radius Scale

```css
--radius-sm:   4px;
--radius-md:   8px;
--radius-lg:  12px;
--radius-xl:  16px;
--radius-full: 9999px;
```

### 7.2 Radius Guidelines

| Component | Radius | Rationale |
|-----------|--------|-----------|
| Buttons | `--radius-md` (8px) | Consistent interactive feel |
| Inputs | `--radius-md` (8px) | Matches buttons |
| Cards | `--radius-lg` (12px) | Distinct surface boundary |
| Panels | `--radius-lg` (12px) | Matches cards |
| Modals | `--radius-lg` (12px) | Integrated with panels |
| Badges, dots | `--radius-full` | Pill shape |
| Avatars | `--radius-full` | Circular |
| Code blocks | `--radius-md` (8px) | Content containers |
| Send button | `--radius-full` | Circular action |

---

## 8. Motion

### 8.1 Duration Tokens

```css
--duration-fast:   150ms;
--duration-normal: 250ms;
--duration-slow:   400ms;
```

### 8.2 Easing Curves

```css
--ease-standard:    cubic-bezier(0.4, 0, 0.2, 1);
--ease-decelerate:  cubic-bezier(0, 0, 0.2, 1);
--ease-emphasized:  cubic-bezier(0.4, 0, 0, 1);
```

### 8.3 Animation Standards

| Use Case | Duration | Easing | Property |
|----------|----------|--------|----------|
| Sidebar collapse/expand | `--duration-normal` | `--ease-standard` | width |
| Button hover | `--duration-fast` | `--ease-standard` | background, opacity |
| Message appearance | `--duration-fast` | `--ease-decelerate` | opacity, transform |
| Progress bar fill | `--duration-normal` | `--ease-standard` | width |
| Modal open | `--duration-normal` | `--ease-decelerate` | opacity, transform |
| Typing indicator | 1.4s | ease-in-out | transform, opacity |
| Skeleton pulse | 1.5s | ease-in-out | opacity |
| Spinner | 0.6s | linear | transform: rotate |
| Voice pulse ring | 1.5s | ease-in-out | box-shadow |
| Permission card pulse | 2s | ease-in-out | border-color |

### 8.4 Scale Transforms

```css
--scale-hover: 1.03;
--scale-press: 0.97;
```

Used on interactive elements like the send button for tactile feedback.

### 8.5 Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  .pr-sidebar { transition: none; }
}
```

All animations should respect the `prefers-reduced-motion` media query. Key animations to disable: sidebar transitions, message entrance animations, pulse animations, skeleton animations.

---

## 9. Component Primitives

### 9.1 Button (`pr-btn`)

| Prop | Values | Default |
|------|--------|---------|
| Variant | `primary` / `secondary` / `ghost` / `danger` | `primary` |
| Size | `sm` (28px) / `md` (36px) / `lg` (44px) | `md` |
| State | default / hover / active / disabled / loading | — |

**Visual spec:**
- Border: `1px solid transparent` (except secondary/ghost)
- Border-radius: `--radius-md`
- Font: `--font-sans`, `--weight-medium`
- Transition: all `--duration-fast`
- Focus-visible: `2px solid var(--accent)` outline, 2px offset
- Loading: spinner animation replaces icon, `aria-busy`
- Disabled: opacity 0.5, `cursor: not-allowed`, `pointer-events: none`
- Icon-only: square dimensions matching height

### 9.2 Input (`pr-input`)

| Prop | Values | Default |
|------|--------|---------|
| Label | Optional text | — |
| Error | Optional error message | — |
| Hint | Optional hint text | — |

**Visual spec:**
- Padding: `--space-2` `--space-3`
- Background: `--bg-primary`
- Border: `1px solid var(--border)`, `--radius-md`
- Height: 36px
- Focus: `border-color: var(--accent)`
- Error: `border-color: var(--error)`
- Disabled: opacity 0.5
- Placeholder: opacity 0.6

### 9.3 Card (`pr-card`)

| Variant | Spec |
|---------|------|
| `elevated` | `box-shadow: var(--shadow-md)` |
| `outlined` | `1px solid var(--border)` |
| `filled` | `background: var(--bg-tertiary)` |

**Padding options:** none (0), sm (12px), md (16px), lg (24px)

### 9.4 Badge (`pr-badge`)

| Variant | Background (color-mix) | Text Color |
|---------|----------------------|------------|
| `default` | `--bg-tertiary` + border | `--text-secondary` |
| `success` | `--success` @ 20% | `--success` |
| `warning` | `--warning` @ 20% | `--warning` |
| `error` | `--error` @ 20% | `--error` |
| `info` | `--accent` @ 20% | `--accent` |

**Sizes:** sm (18px height), md (24px height)

### 9.5 Surface (`pr-surface`)

| Variant | Background |
|---------|------------|
| `primary` | `--surface-primary` |
| `secondary` | `--surface-secondary` |
| `elevated` | `--surface-elevated` |
| `floating` | `--surface-floating` + `--shadow-md` |
| `panel` | `--surface-panel` + border + `--radius-lg` |

### 9.6 Panel (`pr-panel`)

Three-zone container:
- **Header:** `--space-3` `--space-4`, border-bottom, flex row, justify-content: space-between
- **Body:** `--space-4` padding
- **Footer:** `--space-3` `--space-4`, border-top, flex row, justify-content: flex-end

---

## 10. Conversation Component Tokens

### 10.1 Messages

| Role | Avatar | Body Background | Corner Radius |
|------|--------|----------------|---------------|
| User | `var(--accent)` bg, "U", white text | `var(--accent)` bg, white text | `--radius-lg` top, `--radius-sm` bottom-right |
| Assistant | `--bg-tertiary` bg, "E", border | `--bg-tertiary` bg | `--radius-lg` top, `--radius-sm` bottom-left |
| System | transparent, "S" | None (centered) | — |

- Message max-width: 75% (user/assistant), 90% (system)
- Message gap: `--space-3`
- Content gap: `--space-1`
- Entrance animation: `pr-msg-in` — opacity 0→1, translateY 4→0, `--duration-fast`, `--ease-decelerate`

### 10.2 Composer

- Padding: `--space-3` `--space-4`
- Background: `--surface-secondary`
- Border-top: `1px solid var(--color-border)`
- Max-width: 800px, centered
- Textarea: auto-resize, min-height 40px, max-height 200px
- Send button: 40×40px, `--radius-full`, accent background, hover scale transform

### 10.3 Code Block

- Header: `--bg-tertiary`, uppercase language label, copy button
- Body: `--bg-primary`, `--font-mono` at `--text-sm`
- Border: `1px solid var(--color-border)`, `--radius-md`

### 10.4 Typing Indicator

- Three dots, 6px width, `--radius-full`
- Bounce animation: 1.4s, staggered delays 0s/0.2s/0.4s
- Opacity: 0.4 (rest) → 1.0 (peak), translateY -4px

### 10.5 Streaming Cursor

- 2px wide, `1em` height, accent color
- Blink animation: 0.8s step-end, 50% opacity 0

---

## 11. Execution Component Tokens

### 11.1 Execution Card (`pr-exec-card`)

| Status | Border Mix | Icon Color |
|--------|-----------|------------|
| Running | `--execution-running` @ 40% | `--execution-running` |
| Completed | `--execution-completed` @ 30% | `--execution-completed` |
| Failed | `--execution-failed` @ 30% | `--execution-failed` |

### 11.2 Execution Badge (`pr-exec-badge`)

Color-mix backgrounds at 15-20% opacity with matching text color for each status (planning, running, streaming, completed, failed, waiting, permission, retrying, paused, cancelled, skipped, partial, pending, queued).

Compact mode: 8×8px dot, text-indent: -9999px.

### 11.3 Execution Progress

- Track height: 4px, `--radius-full`
- Fill: `--execution-running`, transition width `--duration-normal`
- Indeterminate: 30% width, slides across 1.5s

### 11.4 Permission Card

- Background: `--execution-permission` @ 10%
- Border: `--execution-permission` @ 25%
- Pulse animation: 2s, border-color oscillates

### 11.5 Recovery Card

- Background: `--execution-waiting` @ 10%
- Border: `--execution-waiting` @ 25%

---

## 12. Memory Workspace Tokens

### 12.1 Memory Card (`mw-card`)

- Badge: `mw-badge` variants per super type (action, observation, knowledge, artifact, entity, meta)
- Importance bar: progress fill with `--color-accent`
- Confidence bar: progress fill with `--color-success`
- Pin indicator: 📌 emoji
- Tags: `mw-badge-meta` style
- Timestamp: relative format (just now, Xm ago, Xh ago, date)

### 12.2 Memory Sidebar

- Search input at top, full width
- Section items with icon + label + optional count badge
- Active item highlighted with accent color
- Keyboard accessible (Enter/Space to activate)

---

## 13. Z-Index Scale

```css
--z-dropdown: 100;
--z-overlay:  1000;
--z-modal:    1100;
```

| Layer | Z-Index | Components |
|-------|---------|------------|
| Base content | auto | Everything in normal flow |
| Sidebar resize handle | `--z-dropdown` | Resize gutter |
| Dropdowns | `--z-dropdown` | Tooltips, command palette |
| Overlay backdrops | `--z-overlay` | Settings, plugin, tool panel backdrops |
| Modals | `--z-modal` | Permission dialogs, inspectors |

---

## 14. Dark / Light Theme

### 14.1 Theme Switching

Applied via `.light` class on a parent element (typically `.app`):

```typescript
const [theme, setTheme] = useState<"light" | "dark">("dark");
// toggle: setTheme(t => t === "dark" ? "light" : "dark")
return <div className={`app ${theme}`}>...</div>;
```

### 14.2 Theme Differences

| Token | Dark | Light | Delta |
|-------|------|-------|-------|
| `--bg-primary` | `#1a1a2e` | `#ffffff` | 85% lighter |
| `--bg-secondary` | `#16213e` | `#f5f5f5` | 88% lighter |
| `--bg-tertiary` | `#0f3460` | `#e8e8e8` | 84% lighter |
| `--text-primary` | `#e0e0e0` | `#1a1a2e` | Inverted |
| `--text-secondary` | `#a0a0a0` | `#666666` | 36% darker |
| `--accent` | `#7c73ff` | `#6c63ff` | 8% darker |
| `--border` | `#2a2a4a` | `#e0e0e0` | 82% lighter |
| `--shadow-sm` | 30% black | 8% black | Softer in light |
| `--shadow-md` | 30% black | 10% black | Softer in light |
| `--shadow-lg` | 30% black | 12% black | Softer in light |
| `--surface-overlay` | 50% black | 30% black | Lighter overlay |
| `--color-text-muted` | 50% text-primary | 40% text-primary | More transparent |

Accent colors remain visually similar across themes (perceptual consistency). Code block backgrounds invert: dark `#1a1a2e`, light `#f8f8f8`.

---

## 15. Responsive Rules

### 15.1 Message Timeline

```css
.pr-timeline-inner {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
}
```

### 15.2 Panel Widths

| Panel | Max Width | Min Width |
|-------|-----------|-----------|
| Settings (normal) | 480px | 320px |
| Settings (wide) | 600px | 400px |
| Command palette | 560px | 320px |
| Vision panel | 520px | 340px |
| Notification panel | 320px | 280px |
| Permission dialog | 400px | 320px |

Panels cap at `max-height: 80vh` to always remain within the viewport.

### 15.3 Sidebar Collapse

At narrow viewport widths, the sidebar can collapse to `52px` (icon-only mode). Navigation items show tooltips when collapsed.

---

## 16. Accessibility

### 16.1 Focus Indicators

```css
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
```

Applied to: buttons, inputs, sidebar items, resize handles, command items, memory cards, list items.

### 16.2 ARIA Roles

| Component | Role | Additional |
|-----------|------|------------|
| Sidebar | `navigation` | `aria-label="Main navigation"` |
| Sidebar items | `menuitem` | `aria-current="page"` |
| Tab list | `tablist` | — |
| Individual tab | `tab` | `aria-selected` |
| Dialog/Modal | `dialog` | `aria-modal="true"` |
| Command palette | `dialog` | `aria-label="Command palette"` |
| Results list | `listbox` | `aria-label="Command results"` |
| Result options | `option` | `aria-selected` |
| Log area | `log` | `aria-live="polite"` |
| Error alerts | `alert` | — |
| Status updates | `status` | `aria-live="polite"` for loading |
| Progress bars | `progressbar` | `aria-valuenow/min/max` |
| Toolbar | `toolbar` | `aria-label` |
| Split pane gutter | `separator` | `aria-valuemin/max/now` |
| Breadcrumb | `navigation` | `aria-label="Breadcrumb"` |
| Search region | `search` | `aria-label` |

### 16.3 Color Contrast

All text/background combinations meet WCAG 2.2 AA:
- `--text-primary` on `--bg-primary`: ratio ~12:1 (dark), ~14:1 (light)
- `--text-secondary` on `--bg-primary`: ratio ~7:1 (dark), ~8:1 (light)
- `--accent` on `--bg-primary`: ratio ~6:1 (dark), ~7:1 (light)

### 16.4 Keyboard Navigation

| Action | Key | Component |
|--------|-----|-----------|
| Open command palette | Ctrl+K | Global |
| Toggle settings | Ctrl+, | Global |
| Toggle plugins | Ctrl+P | Global |
| Toggle tools | Ctrl+T | Global |
| Toggle voice | Ctrl+M | Global |
| Toggle vision | Ctrl+I | Global |
| Send message | Enter (textarea) | Composer |
| New line | Shift+Enter | Composer |
| Select next | ArrowDown | Command list |
| Select previous | ArrowUp | Command list |
| Confirm | Enter | Command list |
| Close | Escape | All modals/overlays |
| Resize splitter | Arrow keys | SplitPane gutter |

---

## 17. Interaction States

### 17.1 Button States

```
Default     → background: var(--variant-bg), color: var(--variant-text)
Hover       → opacity: 0.9 / darker background
Active      → transform: scale(0.97)
Focus       → outline: 2px solid var(--accent), offset: 2px
Disabled    → opacity: 0.5, cursor: not-allowed, pointer-events: none
Loading     → spinner replaces icon, aria-busy="true"
```

### 17.2 Input States

```
Default     → border: 1px solid var(--border)
Focus       → border-color: var(--accent)
Hover       → no visual change (handled at parent)
Error       → border-color: var(--error), error text below
Disabled    → opacity: 0.5, cursor: not-allowed
Placeholder → opacity: 0.6
```

### 17.3 Sidebar Item States

```
Default     → background: transparent, color: var(--color-text-secondary)
Hover       → background: var(--surface-elevated), color: var(--color-text-primary)
Active      → background: var(--surface-elevated), color: var(--color-accent)
Active indicator → 3px left accent bar
Focus       → outline: 2px solid var(--color-accent), offset: -2px
Disabled    → opacity: 0.4, cursor: not-allowed
```

---

## 18. Icons & Illustrations

### 18.1 Icon System

Eve OS uses a pragmatic icon approach:
- **Inline SVG** for critical UI icons (send button, mic, camera, interrupt)
- **Emoji text** for contextual indicators (pins, notifications, status dots)
- **Text markers** for categories in the command palette (`[A]`, `[W]`, `[T]`, etc.)
- **Unicode symbols** for common actions (⌘, ⚙, ≡)

### 18.2 Icon Sizing

| Context | Size | Format |
|---------|------|--------|
| Button icons | 14-18px | SVG |
| Sidebar item icons | 20px | emoji / text |
| Empty state icons | 48px | SVG / emoji |
| Avatar | 32px | Text initial |
| Badge dot | 6-8px | CSS |

---

## 19. Design Language Patterns

### 19.1 Overlay Pattern

All overlays (settings, plugins, tools, vision, permissions) follow a consistent pattern:
1. Fixed position `inset: 0`
2. Semi-transparent backdrop: `rgba(0,0,0,0.5)` (dark) / `rgba(0,0,0,0.3)` (light)
3. Centered panel with `--shadow-lg`
4. `z-index: var(--z-overlay)` or `var(--z-modal)`
5. Click-outside-to-close
6. Escape key to close

### 19.2 Empty State Pattern

```
┌──────────────────────────────────────┐
│                                      │
│           [icon 48px]                │
│                                      │
│       Concise title                  │
│       Supporting description         │
│                                      │
│    [Optional action button]          │
│                                      │
│    ┌──────────────────────────────┐  │
│    │ Keyboard shortcut hints      │  │
│    └──────────────────────────────┘  │
│                                      │
└──────────────────────────────────────┘
```

### 19.3 Loading Pattern

```
┌──────────────────────────────────┐
│  ████████░░░░░░░░░░  60%         │  (skeleton bars)
│  ██████████████░░░░  80%         │
│  ██████░░░░░░░░░░░░  40%         │
└──────────────────────────────────┘
```

Skeleton bars pulse at 1.5s, varying widths (60%, 80%, 45%) to create organic feel.

### 19.4 Error State Pattern

```
┌──────────────────────────────────┐
│  ⚠  Error message text    [Retry]│
└──────────────────────────────────┘
```

Error background: `color-mix(in srgb, var(--error) 15%, transparent)`
Error border: `color-mix(in srgb, var(--error) 30%, transparent)`

---

## 20. Future Design Tokens (Reserved)

These tokens are reserved for future expansion and are not yet implemented:

```css
/* Animation curves — reserved */
--ease-spring: spring(300, 30, 10);
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);

/* Additional shadows — reserved */
--shadow-inner: inset 0 1px 3px rgba(0,0,0,0.15);
--shadow-glow: 0 0 20px var(--accent);

/* Gradient tokens — reserved */
--gradient-accent: linear-gradient(135deg, var(--accent), #a78bfa);
--gradient-surface: linear-gradient(180deg, var(--bg-primary), var(--bg-secondary));

/* Scrollbar — reserved */
--scrollbar-width: 8px;
--scrollbar-track: var(--bg-primary);
--scrollbar-thumb: var(--border);

/* Transition durations — reserved */
--duration-instant: 50ms;
--duration-glacial: 600ms;

/* Container queries — reserved */
--content-compact: < 480px;
--content-normal: 480-960px;
--content-wide: > 960px;

/* Focus ring — reserved */
--focus-ring: 0 0 0 3px color-mix(in srgb, var(--accent) 40%, transparent);
```

---

## Appendix A: CSS Custom Property Reference

```
Spacing:      --space-{1,2,3,4,5,6,8,10,12,16}
Typography:   --font-{sans,mono}
Font Size:    --text-{xs,sm,base,lg,xl,2xl,3xl}
Font Weight:  --weight-{normal,medium,semibold,bold}
Line Height:  --leading-{none,tight,normal,relaxed}
Border Radius: --radius-{sm,md,lg,xl,full}
Shadows:      --shadow-{sm,md,lg}
Z-Index:      --z-{dropdown,overlay,modal}
Duration:     --duration-{fast,normal,slow}
Easing:       --ease-{standard,decelerate,emphasized}
Scale:        --scale-{hover,press}
Surface:      --surface-{primary,secondary,sidebar,floating,overlay,elevated,panel,muted}
Text Color:   --color-text-{primary,secondary,muted}
Border Color: --color-border{,hover,active}
Feedback:     --color-{accent,success,warning,error}
Execution:    --execution-{running,completed,failed,waiting,permission}
Layout:       --{sidebar,topbar,statusbar}-{width,height}
```

## Appendix B: Quick Reference — Component Class Naming

| Prefix | Feature Area |
|--------|-------------|
| `pr-*` | Core primitives and components |
| `pr-conv-*` | Conversation / chat |
| `pr-msg-*` | Messages |
| `pr-timeline-*` | Timeline entries |
| `pr-composer-*` | Message composer |
| `pr-exec-*` | Execution display |
| `pr-cmd-*` | Command palette |
| `pr-inspector-*` | Session inspector |
| `pr-activity-*` | Activity center |
| `pr-surface-*` | Surface variants |
| `pr-panel-*` | Panel containers |
| `pr-split-pane-*` | Split pane layout |
| `pr-code-block-*` | Code blocks |
| `pr-md-*` | Markdown rendering |
| `mw-*` | Memory workspace |
| `voice-*` | Voice components |
| `vision-*` | Vision components |
| `settings-*` | Settings panel |
| `plugin-*` | Plugin manager |
| `tool-*` | Tool center |
| `workspace-*` | Workspace data panel |

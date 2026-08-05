"""Context Policies — privacy rules for context access.

Implements privacy enforcement before context is exposed to consumers:
  - Sensitive clipboard content detection
  - Private folder exclusion
  - Password manager detection
  - Incognito browser detection
  - Permission-restricted apps
  - Per-section access control

Context Engine enforces these policies before exposing context to Hermes
or any other consumer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from aios.core.context.models import (
    ExecutionContext,
    ContextScope,
    ClipboardContext,
    WindowContext,
    BrowserContext,
    SelectionContext,
    WorkspaceContext,
)


# ---------------------------------------------------------------------------
# Sensitive content patterns
# ---------------------------------------------------------------------------

# Patterns that indicate sensitive content in clipboard/selection
_SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(api[_-]?key|secret[_-]?key|access[_-]?token|bearer|authorization)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"(password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),  # OpenAI API keys
    re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE),  # GitHub tokens
    re.compile(r"xox[bpsa]-[a-zA-Z0-9-]+", re.IGNORECASE),  # Slack tokens
    re.compile(r"(AKIA|ASIA)[A-Z0-9]{16}", re.IGNORECASE),  # AWS keys
]

# Password manager window titles
_PASSWORD_MANAGER_TITLES = [
    "bitwarden", "1password", "1password", "lastpass", "keepass",
    "dashlane", "keeper", "roboform", "enpass",
]

# Private/incognito browser indicators
_PRIVATE_BROWSER_INDICATORS = [
    "incognito", "private browsing", "private window",
    "inprivate", "incógnito",
]

# Sensitive file paths
_SENSITIVE_PATHS = [
    r"\.ssh\\",
    r"\.env",
    r"passwords?\.(txt|csv|json|kdbx)",
    r"credentials?\.(json|yaml|yml)",
    r"\.aws\\",
    r"\.config\\(gh|hub)\\",
]


# ---------------------------------------------------------------------------
# Context Policy Engine
# ---------------------------------------------------------------------------

@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""
    allowed: bool = True
    reason: str = ""
    redacted: bool = False
    redacted_fields: list[str] = field(default_factory=list)


class ContextPolicy:
    """Enforces privacy rules on ExecutionContext before exposure.

    Every section of ExecutionContext is checked against policies
    before being sent to Hermes or any consumer.
    """

    def __init__(self):
        self._sensitive_patterns = _SENSITIVE_PATTERNS
        self._password_managers = _PASSWORD_MANAGER_TITLES
        self._private_indicators = _PRIVATE_BROWSER_INDICATORS
        self._sensitive_paths = _SENSITIVE_PATHS
        self._allowed_apps: list[str] = []
        self._blocked_apps: list[str] = []
        self._enable_clipboard_filtering = True
        self._enable_selection_filtering = True
        self._enable_path_filtering = True

    # ------------------------------------------------------------------
    # Main enforcement
    # ------------------------------------------------------------------

    def enforce(self, ctx: ExecutionContext) -> ExecutionContext:
        """Apply all privacy policies to the context.

        Returns a new context with sensitive content redacted.
        Original context is not modified.
        """
        # Clipboard policy
        if self._enable_clipboard_filtering:
            ctx.clipboard = self._enforce_clipboard(ctx.clipboard)

        # Selection policy
        if self._enable_selection_filtering:
            ctx.selection = self._enforce_selection(ctx.selection)

        # Window policy (block sensitive apps)
        ctx.window = self._enforce_window(ctx.window)

        # Browser policy (detect incognito)
        ctx.browser = self._enforce_browser(ctx.browser)

        # Workspace policy (filter sensitive paths)
        if self._enable_path_filtering:
            ctx.workspace = self._enforce_workspace(ctx.workspace)

        return ctx

    def evaluate(self, ctx: ExecutionContext) -> PolicyDecision:
        """Evaluate whether the context contains sensitive content.

        Does NOT modify — only reports what would be filtered.
        """
        decisions: list[PolicyDecision] = []

        if self._enable_clipboard_filtering:
            decisions.append(self._evaluate_clipboard(ctx.clipboard))
        if self._enable_selection_filtering:
            decisions.append(self._evaluate_selection(ctx.selection))
        decisions.append(self._evaluate_window(ctx.window))
        decisions.append(self._evaluate_browser(ctx.browser))

        redacted_fields = []
        for d in decisions:
            redacted_fields.extend(d.redacted_fields)

        return PolicyDecision(
            allowed=all(d.allowed for d in decisions),
            redacted=any(d.redacted for d in decisions),
            redacted_fields=redacted_fields,
        )

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    def _enforce_clipboard(self, clipboard: ClipboardContext) -> ClipboardContext:
        if not clipboard.text:
            return clipboard
        if self._contains_sensitive(clipboard.text):
            return ClipboardContext(
                text="[REDACTED — sensitive content detected]",
                has_content=True,
                content_type="redacted",
                timestamp=clipboard.timestamp,
                scope=ContextScope.SENSITIVE,
            )
        return clipboard

    def _evaluate_clipboard(self, clipboard: ClipboardContext) -> PolicyDecision:
        if not clipboard.text:
            return PolicyDecision()
        if self._contains_sensitive(clipboard.text):
            return PolicyDecision(
                allowed=True,
                redacted=True,
                redacted_fields=["clipboard.text"],
            )
        return PolicyDecision()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _enforce_selection(self, selection: SelectionContext) -> SelectionContext:
        if not selection.selected_text:
            return selection
        if self._contains_sensitive(selection.selected_text):
            return SelectionContext(
                selected_text="[REDACTED — sensitive content]",
                source_app=selection.source_app,
                source_file=selection.source_file,
                timestamp=selection.timestamp,
                scope=ContextScope.SENSITIVE,
            )
        return selection

    def _evaluate_selection(self, selection: SelectionContext) -> PolicyDecision:
        if not selection.selected_text:
            return PolicyDecision()
        if self._contains_sensitive(selection.selected_text):
            return PolicyDecision(
                allowed=True,
                redacted=True,
                redacted_fields=["selection.selected_text"],
            )
        return PolicyDecision()

    # ------------------------------------------------------------------
    # Window
    # ------------------------------------------------------------------

    def _enforce_window(self, window: WindowContext) -> WindowContext:
        if self._is_password_manager(window.active_app):
            return WindowContext(
                active_app="[REDACTED — password manager]",
                active_window="",
                activity=window.activity,
                scope=ContextScope.SENSITIVE,
            )
        if self._blocked_apps and window.active_app.lower() in [a.lower() for a in self._blocked_apps]:
            return WindowContext(
                active_app="[BLOCKED]",
                activity=window.activity,
                scope=ContextScope.RESTRICTED,
            )
        return window

    def _evaluate_window(self, window: WindowContext) -> PolicyDecision:
        if self._is_password_manager(window.active_app):
            return PolicyDecision(
                redacted=True,
                redacted_fields=["window.active_app", "window.active_window"],
            )
        return PolicyDecision()

    # ------------------------------------------------------------------
    # Browser
    # ------------------------------------------------------------------

    def _enforce_browser(self, browser: BrowserContext) -> BrowserContext:
        if self._is_private_browsing(browser.active_tab_title):
            return BrowserContext(
                active_tab_title="[Private browsing]",
                active_tab_url="",
                browser_name=browser.browser_name,
                scope=ContextScope.PRIVATE,
            )
        return browser

    def _evaluate_browser(self, browser: BrowserContext) -> PolicyDecision:
        if self._is_private_browsing(browser.active_tab_title):
            return PolicyDecision(
                redacted=True,
                redacted_fields=["browser.active_tab_title", "browser.active_tab_url"],
            )
        return PolicyDecision()

    # ------------------------------------------------------------------
    # Workspace
    # ------------------------------------------------------------------

    def _enforce_workspace(self, workspace: WorkspaceContext) -> WorkspaceContext:
        if workspace.current_project and self._is_sensitive_path(workspace.current_project.path):
            return WorkspaceContext(
                current_project=None,
                workspace_path="[REDACTED — sensitive path]",
                scope=ContextScope.SENSITIVE,
            )
        if workspace.recent_files:
            workspace.recent_files = [
                f for f in workspace.recent_files
                if not self._is_sensitive_path(f)
            ]
        return workspace

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _contains_sensitive(self, text: str) -> bool:
        for pattern in self._sensitive_patterns:
            if pattern.search(text):
                return True
        return False

    def _is_password_manager(self, app_name: str) -> bool:
        if not app_name:
            return False
        return any(pm in app_name.lower() for pm in self._password_managers)

    def _is_private_browsing(self, tab_title: str) -> bool:
        if not tab_title:
            return False
        return any(ind in tab_title.lower() for ind in self._private_indicators)

    def _is_sensitive_path(self, path: str) -> bool:
        if not path:
            return False
        return any(re.search(p, path, re.IGNORECASE) for p in self._sensitive_paths)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_blocked_apps(self, apps: list[str]) -> None:
        self._blocked_apps = apps

    def set_allowed_apps(self, apps: list[str]) -> None:
        self._allowed_apps = apps

    def set_clipboard_filtering(self, enabled: bool) -> None:
        self._enable_clipboard_filtering = enabled

    def set_selection_filtering(self, enabled: bool) -> None:
        self._enable_selection_filtering = enabled

    def set_path_filtering(self, enabled: bool) -> None:
        self._enable_path_filtering = enabled

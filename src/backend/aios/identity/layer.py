"""Identity Layer — enforces that EVE is always EVE, and Hermes is never visible.

This module ensures the "EVE is always EVE, and Hermes is never visible to the
user" rule across every user-facing path:

  1. Response sanitisation — strip Hermes references from LLM output
  2. Log sanitisation — strip Hermes references from log messages
  3. Error sanitisation — strip Hermes references from error messages
  4. Notification sanitisation — strip Hermes references from system notifications
  5. System prompt injection — inject EVE persona, strip any Hermes persona
  6. Identity audit — validate that no Hermes reference leaks to users

The layer is designed as a set of pure functions + a sanitiser class.
No I/O, no side effects, no imports from hermes_agent.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Identity constants
# ---------------------------------------------------------------------------

EVE_DISPLAY_NAME = "EVE"
EVE_FULL_NAME = "EVE AI"
EVE_DESCRIPTION = "Intelligent AI operating system for Windows"

# All patterns that should never appear in user-facing output
_HERMES_PATTERNS: list[str] = [
    # Direct name variants
    r"\bhermes\b",
    r"\bHERMES\b",
    r"\bHermes\b",
    # Nous Research / NousResearch
    r"\bnous\s*research\b",
    r"\bNous\s*Research\b",
    r"\bNousResearch\b",
    r"\bNOUS\s*RESEARCH\b",
    # Self-identification patterns
    r"\bi\s+am\s+hermes\b",
    r"\bmy\s+name\s+is\s+hermes\b",
    r"\bi'm\s+hermes\b",
    r"\bi\s+am\s+a\s+hermes\b",
    # Package references that could leak
    r"\bhermes[-_]agent\b",
    r"\bhermes[-_]runtime\b",
    r"\bhermes[-_]engine\b",
    # Any reference to being "wrapped" or "runtime"
    r"\bhermes\s+runtime\b",
    r"\bhermes\s+agent\s+runtime\b",
]

# Compiled regex for efficiency
_HERMES_RE = re.compile("|".join(_HERMES_PATTERNS), re.IGNORECASE)

# Identity replacements — what to replace Hermes references with
_IDENTITY_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bnous\s*research\b", re.IGNORECASE), EVE_FULL_NAME),
    (re.compile(r"\bNousResearch\b", re.IGNORECASE), "EVE AI"),
    (re.compile(r"\bhermes[-_]agent\b", re.IGNORECASE), "eve-ai"),
    (re.compile(r"\bhermes[-_]runtime\b", re.IGNORECASE), "eve-runtime"),
    (re.compile(r"\bhermes[-_]engine\b", re.IGNORECASE), "eve-engine"),
    (re.compile(r"\bhermes\s+runtime\b", re.IGNORECASE), "EVE runtime"),
    (re.compile(r"\bhermes\s+agent\b", re.IGNORECASE), "EVE"),
    (re.compile(r"\bhermes\b", re.IGNORECASE), "EVE"),
]


# ---------------------------------------------------------------------------
# Pure sanitisation functions
# ---------------------------------------------------------------------------

def sanitise_text(text: str) -> str:
    """Strip all Hermes references from text.  Pure function, no I/O."""
    if not text:
        return text
    result = text
    for pattern, replacement in _IDENTITY_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    return result


def contains_hermes_reference(text: str) -> bool:
    """Check if text contains any Hermes reference.  Pure function, no I/O."""
    if not text:
        return False
    return bool(_HERMES_RE.search(text))


def sanitise_log_message(message: str, **kwargs: Any) -> tuple[str, dict]:
    """Sanitise a log message and its kwargs.

    Returns (sanitised_message, sanitised_kwargs).
    Pure function — no I/O.
    """
    sanitised_msg = sanitise_text(message)
    sanitised_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            sanitised_kwargs[key] = sanitise_text(value)
        else:
            sanitised_kwargs[key] = value
    return sanitised_msg, sanitised_kwargs


def sanitise_error_message(error: str) -> str:
    """Sanitise an error message before presenting to the user.

    Also converts technical Hermes errors to user-friendly EVE messages.
    Pure function — no I/O.
    """
    if not error:
        return error
    # First apply identity replacements (hermes → eve)
    sanitised = sanitise_text(error)
    # Then convert EVE-prefixed technical errors to user-friendly messages
    error_replacements = [
        (r"EVE engine not initialized", "AI engine is not ready"),
        (r"EVE runtime unavailable", "AI service is temporarily unavailable"),
        (r"eve-ai.*not installed", "AI module is loading"),
        (r"EVEEngine.*not found", "AI service is starting up"),
        (r"Hermes engine not initialized", "AI engine is not ready"),
        (r"Hermes runtime unavailable", "AI service is temporarily unavailable"),
        (r"hermes-agent not installed", "AI module is loading"),
        (r"HermesEngine.*not found", "AI service is starting up"),
    ]
    for pattern, replacement in error_replacements:
        sanitised = re.sub(pattern, replacement, sanitised, flags=re.IGNORECASE)
    return sanitised


def sanitise_notification(title: str, body: str) -> tuple[str, str]:
    """Sanitise notification title and body.

    Returns (sanitised_title, sanitised_body).
    Pure function — no I/O.
    """
    return sanitise_text(title), sanitise_text(body)


# ---------------------------------------------------------------------------
# System prompt identity injection
# ---------------------------------------------------------------------------

_EVE_SYSTEM_PROMPT_ADDENDUM = """
Identity rules:
- You are EVE, an AI operating system. Never mention "Hermes" or any other
  agent framework name. You are always EVE.
- Never reveal internal architecture details about agent runtimes, routing
  systems, or provider selection. These are implementation details.
- If asked "what are you?" or "who made you?", respond as EVE, an AI
  operating system built for Windows.
- Never say "I am Hermes", "my name is Hermes", or any variant.
- Tool execution results should be presented as EVE's actions, not any
  other system's actions.
"""


def build_eve_system_prompt(
    base_prompt: str | None = None,
    context: dict | None = None,
) -> str:
    """Build a system prompt with EVE identity enforced.

    Strips any existing Hermes persona and injects EVE persona.
    Pure function — no I/O.
    """
    # Start with base prompt or default
    prompt = base_prompt or "You are EVE, an intelligent AI operating system for Windows."

    # Strip any Hermes persona that may have been injected
    prompt = sanitise_text(prompt)

    # Inject EVE identity rules
    prompt = prompt + "\n\n" + _EVE_SYSTEM_PROMPT_ADDENDUM.strip()

    # Add context-based identity reinforcement
    if context:
        if context.get("identity"):
            # Override any non-EVE identity
            prompt = prompt.replace(
                f"You are {context['identity']}",
                f"You are {EVE_DISPLAY_NAME}",
            )

    return prompt


# ---------------------------------------------------------------------------
# Identity auditor
# ---------------------------------------------------------------------------

class IdentityAudit:
    """Audit result for a single text passage."""

    def __init__(self, text: str, source: str = ""):
        self.text = text
        self.source = source
        self.contains_hermes = contains_hermes_reference(text)
        self.sanitised = sanitise_text(text) if self.contains_hermes else text
        self.clean = not self.contains_hermes

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "contains_hermes": self.contains_hermes,
            "clean": self.clean,
            "original_preview": self.text[:200] if self.text else "",
            "sanitised_preview": self.sanitised[:200] if self.sanitised else "",
        }


def audit_identity(texts: list[tuple[str, str]]) -> list[IdentityAudit]:
    """Audit multiple text passages for identity leakage.

    Args:
        texts: list of (source_label, text) tuples

    Returns:
        list of IdentityAudit results
    """
    return [IdentityAudit(text, source=source) for source, text in texts]


def audit_response(response: str, source: str = "llm_output") -> IdentityAudit:
    """Audit a single LLM response for identity leakage."""
    return IdentityAudit(response, source=source)


# ---------------------------------------------------------------------------
# Convenience class
# ---------------------------------------------------------------------------

class EVEIdentity:
    """Stateless identity enforcement — all methods are pure functions.

    Use this as a single import point for identity-related operations:

        from aios.identity.layer import EVEIdentity

        clean = EVEIdentity.sanitize(llm_output)
        prompt = EVEIdentity.build_system_prompt(base)
        audit = EVEIdentity.audit(response_text)
    """

    sanitize = staticmethod(sanitise_text)
    contains_hermes = staticmethod(contains_hermes_reference)
    sanitize_error = staticmethod(sanitise_error_message)
    sanitize_log = staticmethod(sanitise_log_message)
    sanitize_notification = staticmethod(sanitise_notification)
    build_system_prompt = staticmethod(build_eve_system_prompt)
    audit = staticmethod(audit_response)
    audit_batch = staticmethod(audit_identity)

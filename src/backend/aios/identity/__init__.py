"""Identity Layer — enforces EVE identity across all user-facing paths."""
from aios.identity.layer import (
    EVEIdentity,
    EVE_DISPLAY_NAME,
    EVE_FULL_NAME,
    IdentityAudit,
    audit_identity,
    audit_response,
    build_eve_system_prompt,
    contains_hermes_reference,
    sanitise_error_message,
    sanitise_log_message,
    sanitise_notification,
    sanitise_text,
)

__all__ = [
    "EVEIdentity",
    "EVE_DISPLAY_NAME",
    "EVE_FULL_NAME",
    "IdentityAudit",
    "audit_identity",
    "audit_response",
    "build_eve_system_prompt",
    "contains_hermes_reference",
    "sanitise_error_message",
    "sanitise_log_message",
    "sanitise_notification",
    "sanitise_text",
]

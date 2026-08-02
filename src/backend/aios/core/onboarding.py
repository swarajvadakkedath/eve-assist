"""Provider Onboarding Service — add new providers with just name + key.

This replaces the old flow that required the caller to know the exact
adapter class, default endpoint, models endpoint, etc.  The onboarding
service looks up the ProviderDefinition from the registry and fills in
all the blanks.
"""

from __future__ import annotations

from typing import Any

from aios.core.provider_registry import get, all_as_dicts


def get_onboarding_fields(provider_type: str) -> dict[str, Any] | None:
    """Return the fields needed to onboard a provider of the given type.

    The response tells the frontend exactly which fields to render:
    - needs_api_key: whether an API key is required
    - needs_endpoint: whether a custom endpoint URL is required
    - needs_organization: whether an organization field is needed (OpenAI)
    - default_endpoint: pre-filled default endpoint
    - fields: list of {id, label, type, required, placeholder, default}
    """
    definition = get(provider_type)
    if not definition:
        return None

    fields: list[dict[str, Any]] = []

    if definition.api_key_required:
        fields.append({
            "id": "api_key",
            "label": "API Key",
            "type": "password",
            "required": True,
            "placeholder": f"Enter your {definition.display_name} API key",
            "default": "",
        })

    if definition.needs_endpoint:
        fields.append({
            "id": "endpoint_url",
            "label": "Endpoint URL",
            "type": "text",
            "required": True,
            "placeholder": definition.default_endpoint or "https://your-endpoint.com/v1",
            "default": definition.default_endpoint,
        })

    if definition.supports_organization:
        fields.append({
            "id": "organization",
            "label": "Organization",
            "type": "text",
            "required": False,
            "placeholder": "Optional: your organization ID",
            "default": "",
        })

    return {
        "provider_type": definition.provider_type,
        "display_name": definition.display_name,
        "needs_api_key": definition.api_key_required,
        "needs_endpoint": definition.needs_endpoint,
        "needs_organization": definition.supports_organization,
        "default_endpoint": definition.default_endpoint,
        "fields": fields,
    }


def list_onboarding_options() -> list[dict[str, Any]]:
    """Return all available provider types with their onboarding metadata.

    This replaces the old ``/available-types`` endpoint's data source.
    """
    return all_as_dicts()

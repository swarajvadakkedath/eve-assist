"""Tests for W6 — /routing/categories metadata endpoint + provider metadata."""

import json

import pytest

from aios.core.routing_types import CATEGORY_CAPABILITIES, capabilities_for_category


class TestRoutingCategories:
    def test_categories_derive_from_single_source(self):
        from aios.core.smart_router import ROUTING_CATEGORIES

        ids = {c["id"] for c in ROUTING_CATEGORIES}
        assert "general_chat" in ids
        assert "coding" in ids
        assert "vision" in ids
        assert "reasoning" in ids
        assert "fallback" in ids

    def test_categories_include_capabilities(self):
        from aios.core.smart_router import ROUTING_CATEGORIES

        for c in ROUTING_CATEGORIES:
            assert "label" in c
            assert c["capabilities"] == CATEGORY_CAPABILITIES.get(c["id"], [])

    def test_coding_category_requires_tools(self):
        from aios.core.smart_router import ROUTING_CATEGORIES

        coding = next(c for c in ROUTING_CATEGORIES if c["id"] == "coding")
        assert "supports_tools" in coding["capabilities"]
        assert "supports_function_calling" in coding["capabilities"]

    def test_fallback_category_has_no_required_capabilities(self):
        from aios.core.smart_router import ROUTING_CATEGORIES

        fallback = next(c for c in ROUTING_CATEGORIES if c["id"] == "fallback")
        assert fallback["capabilities"] == []


class TestCapabilityHelpers:
    def test_capabilities_for_category(self):
        assert capabilities_for_category("vision") == ["supports_vision", "supports_streaming"]
        assert capabilities_for_category("general_chat") == ["supports_streaming"]
        assert capabilities_for_category("unknown") == []


class TestProviderMetadata:
    def test_all_as_dicts_includes_supports_organization(self):
        from aios.core.provider_registry import all_as_dicts

        types = {t["id"]: t for t in all_as_dicts()}
        assert "supports_organization" in types["openai"]
        assert types["openai"]["supports_organization"] is True

    def test_metadata_fields_present_for_frontend(self):
        from aios.core.provider_registry import all_as_dicts

        for t in all_as_dicts():
            for field in ("id", "name", "needs_endpoint", "default_endpoint", "icon"):
                assert field in t, f"missing {field} in {t['id']}"

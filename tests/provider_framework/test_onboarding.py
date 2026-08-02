"""Tests for onboarding service."""

import pytest
from aios.core.onboarding import get_onboarding_fields, list_onboarding_options


class TestOnboardingFields:
    """Verify onboarding returns correct fields per provider type."""

    def test_openai_fields(self):
        f = get_onboarding_fields("openai")
        assert f is not None
        assert f["needs_api_key"] is True
        assert f["needs_endpoint"] is False
        assert f["needs_organization"] is True
        field_ids = [fi["id"] for fi in f["fields"]]
        assert "api_key" in field_ids
        assert "organization" in field_ids
        assert "endpoint_url" not in field_ids

    def test_ollama_fields(self):
        f = get_onboarding_fields("ollama")
        assert f is not None
        assert f["needs_api_key"] is False
        assert f["needs_endpoint"] is True
        field_ids = [fi["id"] for fi in f["fields"]]
        assert "api_key" not in field_ids
        assert "endpoint_url" in field_ids

    def test_unknown_returns_none(self):
        assert get_onboarding_fields("nonexistent") is None

    def test_all_registered_providers(self):
        """Every registered provider should have onboarding fields."""
        options = list_onboarding_options()
        assert len(options) == 16
        for opt in options:
            f = get_onboarding_fields(opt["id"])
            assert f is not None, f"{opt['id']} missing onboarding fields"


class TestOnboardingOptions:
    """Verify list_onboarding_options returns full registry."""

    def test_count(self):
        options = list_onboarding_options()
        assert len(options) == 16

    def test_has_required_fields(self):
        options = list_onboarding_options()
        for opt in options:
            assert "id" in opt
            assert "name" in opt
            assert "needs_endpoint" in opt

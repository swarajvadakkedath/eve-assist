"""Security tests for credential storage hardening.

Tests:
  1. Secure credential create/read/update/delete
  2. Secure storage unavailable → SecureStorageError raised
  3. Provider creation when secure storage unavailable
  4. No plaintext fallback (providers.json never contains _api_key)
  5. API response contains no secret
  6. Legacy migration succeeds
  7. Legacy migration failure marks provider
  8. Provider deletion removes credential
  9. Multiple provider credentials remain isolated
  10. _save strips _api_key from JSON output
  11. _load_api_key returns None when win32cred unavailable
  12. list_providers never returns _api_key
  13. get_provider never returns _api_key
  14. SecureStorageError carries safe message only
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from aios.core.provider_manager import (
    ProviderManager,
    SecureStorageError,
    HAS_WIN32CRED,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_config(tmp_path):
    """Create a ProviderManager with a temp config dir."""
    config_dir = tmp_path / ".eve"
    config_dir.mkdir()
    return str(config_dir)


@pytest.fixture
def pm(tmp_config):
    """ProviderManager with temp config, no real providers."""
    with patch("aios.core.provider_manager.SmartRouter"), \
         patch("aios.core.provider_manager.HealthMonitor"), \
         patch("aios.core.provider_manager.ModelCache"), \
         patch("aios.core.provider_manager.StreamingManager"):
        return ProviderManager(config_dir=tmp_config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSecureCredentialCRUD:
    """1. Secure credential create/read/update/delete (Windows Credential Manager)."""

    @pytest.mark.skipif(not HAS_WIN32CRED, reason="win32cred not available")
    def test_store_and_load_api_key(self, pm):
        pid = "test-provider-123"
        pm._store_api_key(pid, "sk-test-secret-key-12345")
        loaded = pm._load_api_key(pid)
        assert loaded == "sk-test-secret-key-12345"
        # Cleanup
        pm._delete_api_key(pid)

    @pytest.mark.skipif(not HAS_WIN32CRED, reason="win32cred not available")
    def test_delete_api_key(self, pm):
        pid = "test-provider-delete"
        pm._store_api_key(pid, "sk-delete-me")
        pm._delete_api_key(pid)
        loaded = pm._load_api_key(pid)
        assert loaded is None

    @pytest.mark.skipif(not HAS_WIN32CRED, reason="win32cred not available")
    def test_update_api_key(self, pm):
        pid = "test-provider-update"
        pm._store_api_key(pid, "sk-old-key")
        pm._store_api_key(pid, "sk-new-key")
        loaded = pm._load_api_key(pid)
        assert loaded == "sk-new-key"
        pm._delete_api_key(pid)


class TestSecureStorageUnavailable:
    """2. Secure storage unavailable → SecureStorageError raised."""

    def test_store_raises_when_win32cred_unavailable(self, pm):
        with patch("aios.core.provider_manager.HAS_WIN32CRED", False):
            with pytest.raises(SecureStorageError) as exc_info:
                pm._store_api_key("test", "secret")
            assert "unavailable" in str(exc_info.value).lower()

    def test_load_returns_none_when_win32cred_unavailable(self, pm):
        with patch("aios.core.provider_manager.HAS_WIN32CRED", False):
            result = pm._load_api_key("test")
            assert result is None


class TestProviderCreationWithoutSecureStorage:
    """3. Provider creation when secure storage unavailable."""

    def test_add_provider_marks_secure_storage_unavailable(self, pm):
        with patch("aios.core.provider_manager.HAS_WIN32CRED", False):
            with patch("aios.core.provider_manager.get_catalog_models", return_value=[]):
                result = pm.add_provider(
                    provider_type="openai",
                    name="Test OpenAI",
                    api_key="sk-test-key",
                )
            assert result.get("secure_storage_unavailable") is True

    def test_add_provider_without_api_key_no_error(self, pm):
        with patch("aios.core.provider_manager.get_catalog_models", return_value=[]):
            result = pm.add_provider(
                provider_type="openai",
                name="Test OpenAI",
            )
        assert result.get("secure_storage_unavailable") is not True


class TestNoPlaintextFallback:
    """4. No plaintext fallback — providers.json never contains _api_key."""

    def test_save_strips_api_key(self, pm):
        # Manually inject _api_key into a provider
        pm._providers = [{"id": "test", "type": "openai", "_api_key": "sk-secret"}]
        pm._save()

        # Read the file and verify _api_key is not present
        content = (Path(pm._config_dir) / "providers.json").read_text()
        data = json.loads(content)
        assert "_api_key" not in data[0]
        assert data[0]["id"] == "test"

    def test_save_does_not_write_secret(self, pm):
        pm._providers = [{"id": "x", "_api_key": "sk-super-secret-12345"}]
        pm._save()

        raw = (Path(pm._config_dir) / "providers.json").read_text()
        assert "sk-super-secret" not in raw
        assert "super-secret" not in raw


class TestApiResponseSanitization:
    """5. API response contains no secret."""

    def test_list_providers_strips_api_key(self, pm):
        pm._providers = [
            {"id": "p1", "type": "openai", "_api_key": "sk-secret-1"},
            {"id": "p2", "type": "google", "_api_key": "google-secret-2"},
        ]
        result = pm.list_providers()
        for p in result:
            assert "_api_key" not in p

    def test_get_provider_strips_api_key(self, pm):
        pm._providers = [{"id": "p1", "type": "openai", "_api_key": "sk-secret"}]
        result = pm.get_provider("p1")
        assert "_api_key" not in result
        assert result["id"] == "p1"

    def test_list_providers_adds_has_api_key_flag(self, pm):
        pm._providers = [{"id": "p1", "type": "openai"}]
        with patch.object(pm, "_load_api_key", return_value="sk-something"):
            result = pm.list_providers()
            assert result[0]["has_api_key"] is True

    def test_list_providers_has_api_key_false_when_no_key(self, pm):
        pm._providers = [{"id": "p1", "type": "openai"}]
        with patch.object(pm, "_load_api_key", return_value=None):
            result = pm.list_providers()
            assert result[0]["has_api_key"] is False


class TestLegacyMigration:
    """6-7. Legacy credential migration."""

    def test_migrate_legacy_credential(self, pm):
        """Legacy _api_key in provider dict → moved to Windows Credential Manager."""
        pid = "test-migrate-legacy"
        pm._providers = [{"id": pid, "type": "openai", "_api_key": "sk-legacy-key"}]

        if HAS_WIN32CRED:
            pm._migrate_legacy_credentials()
            # Verify _api_key removed from provider
            assert "_api_key" not in pm._providers[0]
            # Verify key stored in credential manager
            loaded = pm._load_api_key(pid)
            assert loaded == "sk-legacy-key"
            # Cleanup
            pm._delete_api_key(pid)
        else:
            # Without win32cred, migration is skipped
            pm._migrate_legacy_credentials()
            # Provider should still exist (migration skipped)

    def test_migrate_failure_marks_provider(self, pm):
        """Failed migration marks provider with credential_migration_required."""
        pid = "test-migrate-fail"
        pm._providers = [{"id": pid, "type": "openai", "_api_key": "sk-key"}]

        with patch("aios.core.provider_manager.HAS_WIN32CRED", True), \
             patch("aios.core.provider_manager.win32cred") as mock_cred:
            mock_cred.CRED_TYPE_GENERIC = 1
            mock_cred.CRED_PERSIST_LOCAL_MACHINE = 2
            mock_cred.CredWrite.side_effect = Exception("Credential write failed")
            pm._migrate_legacy_credentials()

        assert pm._providers[0].get("credential_migration_required") is True


class TestProviderDeletionRemovesCredential:
    """8. Provider deletion removes credential."""

    @pytest.mark.skipif(not HAS_WIN32CRED, reason="win32cred not available")
    def test_remove_provider_deletes_credential(self, pm):
        pid = "test-remove-cred"
        pm._providers = [{"id": pid, "type": "openai", "is_default": False}]
        pm._store_api_key(pid, "sk-to-delete")
        pm.remove_provider(pid)
        loaded = pm._load_api_key(pid)
        assert loaded is None


class TestCredentialIsolation:
    """9. Multiple provider credentials remain isolated."""

    @pytest.mark.skipif(not HAS_WIN32CRED, reason="win32cred not available")
    def test_different_providers_different_keys(self, pm):
        pm._store_api_key("provider-a", "key-a-secret")
        pm._store_api_key("provider-b", "key-b-secret")

        assert pm._load_api_key("provider-a") == "key-a-secret"
        assert pm._load_api_key("provider-b") == "key-b-secret"

        pm._delete_api_key("provider-a")
        pm._delete_api_key("provider-b")

        assert pm._load_api_key("provider-a") is None
        assert pm._load_api_key("provider-b") is None


class TestSaveStripsApiKey:
    """10. _save always strips _api_key from JSON output."""

    def test_save_never_includes_api_key(self, pm):
        pm._providers = [
            {"id": "p1", "_api_key": "secret1"},
            {"id": "p2", "_api_key": "secret2"},
        ]
        pm._save()

        raw = (Path(pm._config_dir) / "providers.json").read_text()
        assert "secret1" not in raw
        assert "secret2" not in raw


class TestLoadApiKeyReturnsNone:
    """11. _load_api_key returns None when win32cred unavailable."""

    def test_returns_none_without_win32cred(self, pm):
        with patch("aios.core.provider_manager.HAS_WIN32CRED", False):
            assert pm._load_api_key("any-provider") is None


class TestListProvidersNoSecret:
    """12. list_providers never returns _api_key in any path."""

    def test_no_api_key_in_any_provider(self, pm):
        pm._providers = [
            {"id": "p1", "_api_key": "secret", "type": "openai"},
            {"id": "p2", "_api_key": "another-secret", "type": "google"},
        ]
        result = pm.list_providers()
        for p in result:
            assert "_api_key" not in p
            assert "secret" not in json.dumps(p)


class TestGetProviderNoSecret:
    """13. get_provider never returns _api_key."""

    def test_no_api_key(self, pm):
        pm._providers = [{"id": "p1", "_api_key": "secret"}]
        result = pm.get_provider("p1")
        assert "_api_key" not in result


class TestSecureStorageErrorSafe:
    """14. SecureStorageError carries safe message only."""

    def test_error_message_no_secret(self):
        err = SecureStorageError("Secure credential storage unavailable")
        msg = str(err)
        assert "secret" not in msg.lower() or msg.lower().count("secret") == 0
        assert "api_key" not in msg.lower()

    def test_error_attributes(self):
        err = SecureStorageError("test error")
        assert str(err) == "test error"

"""STAGE 4: sanitize_error attack tests.

Verify that sanitize_error() properly redacts ALL secret patterns
from error strings before they reach any user-facing surface.
"""

import pytest

from aios.core.adapters.base import sanitize_error


class TestSanitizeOpenAIKeys:
    """OpenAI sk-* key patterns."""

    def test_sk_key_in_error_message(self):
        result = sanitize_error("Authentication failed: sk-ant-example123456789")
        assert "sk-ant-example123456789" not in result
        assert "REDACTED" in result

    def test_sk_key_in_json(self):
        result = sanitize_error('{"error": "invalid api_key: sk-proj-abc123def456ghi789"}')
        assert "sk-proj-abc123def456ghi789" not in result
        assert "REDACTED" in result

    def test_sk_key_in_url(self):
        result = sanitize_error("Request to https://api.openai.com/v1?api_key=sk-test123456789abcdef failed")
        assert "sk-test123456789abcdef" not in result
        assert "REDACTED" in result

    def test_sk_key_with_hyphens(self):
        result = sanitize_error("Error: sk-1234-5678-90ab-cdef")
        assert "sk-1234-5678-90ab-cdef" not in result
        assert "REDACTED" in result


class TestSanitizeAnthropicKeys:
    """Anthropic sk-ant-* key patterns."""

    def test_sk_ant_key(self):
        result = sanitize_error("Auth error: sk-ant-api03-verylongkey123456789")
        assert "sk-ant-api03-verylongkey123456789" not in result
        assert "REDACTED" in result

    def test_sk_ant_key_in_headers(self):
        result = sanitize_error("Header: x-api-key=sk-ant-example-secret-key-here")
        assert "sk-ant-example-secret-key-here" not in result
        assert "REDACTED" in result


class TestSanitizeGoogleKeys:
    """Google AIza* key patterns."""

    def test_aiza_key(self):
        result = sanitize_error("Google API error: AIzaSyExampleSecret12345678901234")
        assert "AIzaSyExampleSecret12345678901234" not in result
        assert "REDACTED" in result

    def test_aiza_key_in_url(self):
        result = sanitize_error("Request failed: https://.googleapis.com?key=AIzaSyTestKey123456789012345")
        assert "AIzaSyTestKey123456789012345" not in result
        assert "REDACTED" in result

    def test_x_goog_api_key_header(self):
        result = sanitize_error("Header x-goog-api-key: AIzaSyAnotherSecretKey123456789")
        assert "AIzaSyAnotherSecretKey123456789" not in result
        assert "REDACTED" in result


class TestSanitizeGroqKeys:
    """Groq gsk_* key patterns."""

    def test_gsk_key(self):
        result = sanitize_error("Groq auth failed: gsk_verylongapikey123456789")
        assert "gsk_verylongapikey123456789" not in result
        assert "REDACTED" in result

    def test_gsk_key_in_json(self):
        result = sanitize_error('{"api_key": "gsk_test123456789abcdef"}')
        assert "gsk_test123456789abcdef" not in result
        assert "REDACTED" in result


class TestSanitizeBearerTokens:
    """Bearer token patterns."""

    def test_bearer_token(self):
        result = sanitize_error("Authorization: Bearer SECRET_TOKEN_VALUE_123456789")
        assert "SECRET_TOKEN_VALUE_123456789" not in result
        assert "REDACTED" in result

    def test_bearer_token_in_header(self):
        result = sanitize_error("Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "REDACTED" in result

    def test_bearer_token_in_error(self):
        result = sanitize_error("401 Unauthorized: Bearer token_abc123def456ghi789jkl012")
        assert "token_abc123def456ghi789jkl012" not in result
        assert "REDACTED" in result


class TestSanitizeApiKeyPatterns:
    """Generic api_key / api-key / apikey patterns."""

    def test_api_key_equals(self):
        result = sanitize_error("api_key=SECRET_API_KEY_VALUE_123456")
        assert "SECRET_API_KEY_VALUE_123456" not in result
        assert "REDACTED" in result

    def test_api_key_colon(self):
        result = sanitize_error("api_key: SECRET_API_KEY_VALUE_123456")
        assert "SECRET_API_KEY_VALUE_123456" not in result
        assert "REDACTED" in result

    def test_api_key_space(self):
        result = sanitize_error("api_key SECRET_API_KEY_VALUE_123456")
        assert "SECRET_API_KEY_VALUE_123456" not in result
        assert "REDACTED" in result

    def test_apikey_equals(self):
        result = sanitize_error("apikey=SECRET_VALUE_123456789")
        assert "SECRET_VALUE_123456789" not in result
        assert "REDACTED" in result

    def test_api_hyphen_key(self):
        result = sanitize_error("api-key=SECRET_VALUE_123456789")
        assert "SECRET_VALUE_123456789" not in result
        assert "REDACTED" in result

    def test_x_api_key_header(self):
        result = sanitize_error("x-api-key: SECRET_VALUE_123456789")
        assert "SECRET_VALUE_123456789" not in result
        assert "REDACTED" in result


class TestSanitizeCombinations:
    """Combined secret patterns in complex strings."""

    def test_multiple_secrets_in_json(self):
        text = '{"error": "auth failed", "api_key": "sk-1234567890abcdef", "bearer": "Bearer tokensecretvalue123456"}'
        result = sanitize_error(text)
        assert "sk-1234567890abcdef" not in result
        assert "tokensecretvalue123456" not in result
        assert "REDACTED" in result

    def test_nested_provider_error(self):
        text = "Provider google returned: Authentication failed (API key: AIzaSySecretKey12345678901234)"
        result = sanitize_error(text)
        assert "AIzaSySecretKey12345678901234" not in result
        assert "REDACTED" in result

    def test_http_exception_body(self):
        text = 'HTTPException(401, detail="Invalid API key: sk-ant-api03-abc123def456ghi789jkl012mno")'
        result = sanitize_error(text)
        assert "sk-ant-api03-abc123def456ghi789jkl012mno" not in result
        assert "REDACTED" in result

    def test_stream_error_event(self):
        text = "Stream failed: Connection to provider lost. Auth header: Bearer gsk_secret123456789abcdef"
        result = sanitize_error(text)
        assert "gsk_secret123456789abcdef" not in result
        assert "REDACTED" in result

    def test_url_with_credentials(self):
        """URL-embedded credentials (user:pass@host) ARE redacted since RC2.
        Pattern: ://user:pass@host -> //[REDACTED]@host
        """
        text = "Failed to connect: https://user:SECRET123@api.example.com/v1/models"
        result = sanitize_error(text)
        assert "SECRET123" not in result  # FIXED in RC2 - now redacted
        assert "REDACTED" in result


class TestSanitizeSafeMetadata:
    """Verify useful metadata is PRESERVED after sanitization."""

    def test_provider_name_preserved(self):
        result = sanitize_error("Provider google returned error: AIzaSySecret12345678901234")
        assert "google" in result
        assert "REDACTED" in result

    def test_http_status_preserved(self):
        result = sanitize_error("HTTP 401: Bearer secrettoken123456789")
        assert "401" in result
        assert "REDACTED" in result

    def test_model_name_preserved(self):
        result = sanitize_error("Model gemini-2.5-flash failed: sk-1234567890abcdef")
        assert "gemini-2.5-flash" in result
        assert "REDACTED" in result

    def test_error_category_preserved(self):
        result = sanitize_error("Authentication failed: api_key=sk-test123456789abcdef")
        assert "Authentication failed" in result
        assert "REDACTED" in result

    def test_retry_after_preserved(self):
        result = sanitize_error("Rate limited. Retry-After: 30s. Bearer token123456789012345")
        assert "30s" in result
        assert "REDACTED" in result

    def test_provider_instance_preserved(self):
        result = sanitize_error("Provider google-personal failed: AIzaSyKey123456789012345")
        assert "google-personal" in result
        assert "REDACTED" in result


class TestSanitizeEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string(self):
        result = sanitize_error("")
        assert result == ""

    def test_no_secrets(self):
        result = sanitize_error("Simple error message with no secrets")
        assert result == "Simple error message with no secrets"

    def test_short_key_not_redacted(self):
        """Keys shorter than minimum length should NOT be redacted."""
        result = sanitize_error("sk-short")
        assert "sk-short" in result

    def test_case_insensitive(self):
        result = sanitize_error("API_KEY=SecretValue123456789")
        assert "SecretValue123456789" not in result
        assert "REDACTED" in result

    def test_unicode_in_text(self):
        result = sanitize_error("Error during request: sk-1234567890abcdef (encoding: utf-8)")
        assert "sk-1234567890abcdef" not in result
        assert "REDACTED" in result

    def test_multiple_same_pattern(self):
        result = sanitize_error("Keys: sk-first123456789 and sk-second123456789")
        assert "sk-first123456789" not in result
        assert "sk-second123456789" not in result
        assert result.count("REDACTED") >= 2

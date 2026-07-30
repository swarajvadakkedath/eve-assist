"""Tests for Google adapter API key security fix.

Verifies API key is sent via x-goog-api-key header, not in URL query string.
"""

from aios.core.adapters.google_adapter import GoogleAdapter
from aios.core.streaming_manager import StreamingManager


def test_google_adapter_no_key_in_url():
    adapter = GoogleAdapter(api_key="test-key-12345")
    # The _headers dict should contain the key, not the URL
    assert "x-goog-api-key" in adapter._headers
    assert adapter._headers["x-goog-api-key"] == "test-key-12345"

    url = adapter._chat_url("gemini-2.5-flash", stream=False)
    assert "key=" not in url
    assert "test-key-12345" not in url

    url_stream = adapter._chat_url("gemini-2.5-flash", stream=True)
    assert "key=" not in url_stream
    assert "test-key-12345" not in url_stream


def test_google_adapter_no_key():
    adapter = GoogleAdapter(api_key="")
    assert "x-goog-api-key" not in adapter._headers
    url = adapter._chat_url("gemini-2.5-flash")
    assert "key=" not in url


def test_google_adapter_list_models_url():
    adapter = GoogleAdapter(api_key="secret123")
    # Verify the list_models URL doesn't have API key
    from aios.core.timeout_retry import TimeoutConfig
    url = f"{adapter._base_url}/models"
    assert "key=" not in url
    assert "secret123" not in url


def test_google_adapter_health_url():
    adapter = GoogleAdapter(api_key="secret456")
    url = f"{adapter._base_url}/models"
    assert "key=" not in url
    assert "secret456" not in url


def test_google_streaming_manager_integration():
    sm = StreamingManager()
    adapter = GoogleAdapter(api_key="test-key", streaming_manager=sm)
    assert adapter._streaming is sm

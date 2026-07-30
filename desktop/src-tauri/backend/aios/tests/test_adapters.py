"""Tests for adapter streaming integration with StreamingManager."""

from aios.core.streaming_manager import StreamingManager
from aios.core.adapters.base import ChatRequest


def test_all_adapters_accept_streaming_manager():
    """Every adapter constructor accepts an optional streaming_manager param."""
    sm = StreamingManager()

    from aios.core.adapters.openai_adapter import OpenAIAdapter
    oa = OpenAIAdapter(api_key="test", streaming_manager=sm)
    assert oa._streaming is sm

    from aios.core.adapters.anthropic_adapter import AnthropicAdapter
    aa = AnthropicAdapter(api_key="test", streaming_manager=sm)
    assert aa._streaming is sm

    from aios.core.adapters.google_adapter import GoogleAdapter
    ga = GoogleAdapter(api_key="test", streaming_manager=sm)
    assert ga._streaming is sm

    from aios.core.adapters.groq_adapter import GroqAdapter
    gra = GroqAdapter(api_key="test", streaming_manager=sm)
    assert gra._streaming is sm

    from aios.core.adapters.ollama_adapter import OllamaAdapter
    ola = OllamaAdapter(streaming_manager=sm)
    assert ola._streaming is sm

    from aios.core.adapters.openai_compatible_adapter import OpenAICompatibleAdapter
    oca = OpenAICompatibleAdapter("test_type", "Test", api_key="test", streaming_manager=sm)
    assert oca._streaming is sm


def test_all_adapters_default_streaming_manager():
    """Every adapter creates a default StreamingManager if none provided."""
    from aios.core.adapters.openai_adapter import OpenAIAdapter
    oa = OpenAIAdapter(api_key="test")
    assert oa._streaming is not None
    assert isinstance(oa._streaming, StreamingManager)

    from aios.core.adapters.google_adapter import GoogleAdapter
    ga = GoogleAdapter(api_key="test")
    assert ga._streaming is not None

    from aios.core.adapters.groq_adapter import GroqAdapter
    gra = GroqAdapter(api_key="test")
    assert gra._streaming is not None


def test_stream_method_signatures():
    """All adapters have stream() returning AsyncIterator[str]."""
    from aios.core.adapters.openai_adapter import OpenAIAdapter
    import inspect
    sig = inspect.signature(OpenAIAdapter.stream)
    assert "request" in sig.parameters

    from aios.core.adapters.anthropic_adapter import AnthropicAdapter
    sig = inspect.signature(AnthropicAdapter.stream)
    assert "request" in sig.parameters

    from aios.core.adapters.google_adapter import GoogleAdapter
    sig = inspect.signature(GoogleAdapter.stream)
    assert "request" in sig.parameters


def test_chat_request_defaults():
    req = ChatRequest(messages=[{"role": "user", "content": "hi"}])
    assert req.model == ""
    assert req.max_tokens == 4096
    assert req.temperature == 0.7
    assert req.stream is False


# ── Regression: Google adapter role normalization (Defect 2) ──────

def test_google_adapter_assistant_role_maps_to_model():
    """GoogleAdapter._build_contents maps 'assistant' role to 'model' role for Gemini API."""
    from aios.core.adapters.google_adapter import GoogleAdapter
    ga = GoogleAdapter(api_key="test")

    messages = [
        {"role": "system", "content": "You are Eve."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]

    contents, system = ga._build_contents(messages)
    assert system == "You are Eve."
    assert len(contents) == 3
    assert contents[0]["role"] == "user"
    assert contents[1]["role"] == "model"
    assert contents[2]["role"] == "user"
    assert contents[1]["parts"][0]["text"] == "Hi there!"


def test_google_adapter_no_assistant_role_in_contents():
    """GoogleAdapter never sends 'assistant' role to Gemini API."""
    from aios.core.adapters.google_adapter import GoogleAdapter
    ga = GoogleAdapter(api_key="test")

    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "Bye"},
        {"role": "assistant", "content": "Goodbye"},
    ]

    contents, _ = ga._build_contents(messages)
    roles = [c["role"] for c in contents]
    assert "assistant" not in roles
    assert roles == ["user", "model", "user", "model"]


def test_google_adapter_system_prompt_extraction():
    """GoogleAdapter extracts system prompt to system_instruction, not in contents."""
    from aios.core.adapters.google_adapter import GoogleAdapter
    ga = GoogleAdapter(api_key="test")

    messages = [
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "Hi"},
    ]

    contents, system = ga._build_contents(messages)
    assert system == "Be concise."
    assert all(c["role"] != "system" for c in contents)


def test_google_adapter_empty_messages_fallback():
    """GoogleAdapter returns a placeholder if no user/assistant messages exist."""
    from aios.core.adapters.google_adapter import GoogleAdapter
    ga = GoogleAdapter(api_key="test")

    contents, _ = ga._build_contents([{"role": "system", "content": "test"}])
    assert len(contents) == 1
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"][0]["text"] == "..."

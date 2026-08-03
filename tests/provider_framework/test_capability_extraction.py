"""Tests for W2 capability extraction + deprecation handling.

These test the pure helper functions in openai_compatible_adapter, so no
network access is required.
"""

import pytest

from aios.core.adapters.openai_compatible_adapter import _extract_capabilities, _extract_deprecation
from aios.core.model_info import AvailabilityStatus


class TestCapabilityExtraction:
    def test_openrouter_modality_vision(self):
        raw = {"id": "openai/gpt-4o", "architecture": {"modality": "text+image", "input_modalities": ["text", "image"]}}
        caps = _extract_capabilities("openai/gpt-4o", raw)
        assert caps["supports_vision"] is True
        assert caps["supports_audio"] is False

    def test_openrouter_input_modalities_audio(self):
        raw = {"architecture": {"input_modalities": ["text", "audio"]}}
        caps = _extract_capabilities("x/y", raw)
        assert caps["supports_audio"] is True

    def test_huggingface_chat_tools_json(self):
        raw = {
            "pipeline_tag": "text-generation",
            "inference": {"chat_completion": {"tags": ["tools", "structured-output"]}},
        }
        caps = _extract_capabilities("meta-llama/Llama-3.3-70B-Instruct", raw)
        assert caps["supports_tools"] is True
        assert caps["supports_function_calling"] is True
        assert caps["supports_json"] is True

    def test_huggingface_embeddings_pipeline(self):
        caps = _extract_capabilities("thenlper/gte-large", {"pipeline_tag": "feature-extraction"})
        assert caps["supports_embeddings"] is True

    def test_huggingface_tts_audio(self):
        caps = _extract_capabilities("openai/whisper-large-v3", {"pipeline_tag": "automatic-speech-recognition"})
        assert caps["supports_audio"] is True

    def test_huggingface_image_generation(self):
        caps = _extract_capabilities("stabilityai/sdxl", {"pipeline_tag": "text-to-image"})
        assert caps["supports_image_generation"] is True

    def test_reasoning_id_heuristic(self):
        assert _extract_capabilities("deepseek-ai/DeepSeek-R1", {})["supports_reasoning"] is True

    def test_embeddings_id_heuristic(self):
        assert _extract_capabilities("text-embedding-3-small", {})["supports_embeddings"] is True

    def test_vision_id_heuristic(self):
        assert _extract_capabilities("llava-v1.5-7b-vision", {})["supports_vision"] is True

    def test_image_generation_id_heuristic(self):
        assert _extract_capabilities("dall-e-3", {})["supports_image_generation"] is True

    def test_audio_id_heuristic(self):
        assert _extract_capabilities("whisper-large-v3", {})["supports_audio"] is True

    def test_explicit_fields_override(self):
        caps = _extract_capabilities("some-model", {"supports_function_calling": True})
        assert caps["supports_function_calling"] is True
        assert caps["supports_tools"] is True

    def test_empty_metadata_all_false(self):
        caps = _extract_capabilities("plain-model", {})
        for v in caps.values():
            assert v is False


class TestDeprecationExtraction:
    def test_status_deprecated(self):
        deprecated, availability = _extract_deprecation({"status": "deprecated"})
        assert deprecated is True
        assert availability == AvailabilityStatus.DEPRECATED

    def test_status_removed(self):
        deprecated, availability = _extract_deprecation({"status": "removed"})
        assert deprecated is True
        assert availability == AvailabilityStatus.REMOVED

    def test_status_preview(self):
        deprecated, availability = _extract_deprecation({"status": "preview"})
        assert deprecated is False
        assert availability == AvailabilityStatus.PREVIEW

    def test_deprecation_field_date(self):
        deprecated, availability = _extract_deprecation({"deprecation": "2026-06-15"})
        assert deprecated is True
        assert availability == AvailabilityStatus.DEPRECATED

    def test_deprecation_field_bool_true(self):
        deprecated, availability = _extract_deprecation({"deprecated": True})
        assert deprecated is True

    def test_available_default(self):
        deprecated, availability = _extract_deprecation({})
        assert deprecated is False
        assert availability == AvailabilityStatus.AVAILABLE

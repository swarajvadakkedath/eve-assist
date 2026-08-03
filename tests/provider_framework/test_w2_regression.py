"""Regression tests for W2 capability extraction regression fixes."""

import pytest

from aios.core.capability_inference import infer_capabilities, bool_from_inference, merge_into_modelinfo
from aios.core.routing_types import RouteCandidate
from aios.core.model_info import ModelInfo


class TestInferenceTriState:
    """Test that inference returns unknown (None) for missing metadata."""

    def test_empty_metadata_all_unknown(self):
        caps = infer_capabilities("plain-model", {})
        for k, v in caps.items():
            assert v is None, f"{k} should be None, got {v}"

    def test_reasoning_unknown_missing_heuristics(self):
        caps = infer_capabilities("some-random-name", {})
        assert caps["supports_reasoning"] is None
        assert caps["supports_thinking"] is None

    def test_empty_metadata_to_bool_all_false(self):
        caps = infer_capabilities("plain-model", {})
        bool_caps = bool_from_inference(caps)
        for k, v in bool_caps.items():
            assert v is False, f"{k} should default to False via bool_from_inference"


class TestInferenceMetaPriority:
    """Test that explicit provider metadata takes highest priority."""

    def test_explicit_false_overrides_heuristic(self):
        caps = infer_capabilities("deepseek-reasoner", {
            "supports_thinking": False,
            "supports_reasoning": False,
        })
        assert caps["supports_thinking"] is False
        assert caps["supports_reasoning"] is False


class TestInferenceHeuristics:
    """Test ID-based heuristics for reasoning, thinking, tools."""

    def test_reasoning_heuristic_o1(self):
        caps = infer_capabilities("o1", {})
        assert caps["supports_reasoning"] is True
        assert caps["supports_thinking"] is True

    def test_reasoning_heuristic_o3(self):
        caps = infer_capabilities("o3-mini", {})
        assert caps["supports_reasoning"] is True
        assert caps["supports_thinking"] is True

    def test_reasoning_heuristic_r1(self):
        caps = infer_capabilities("deepseek-r1", {})
        assert caps["supports_reasoning"] is True
        assert caps["supports_thinking"] is True

    def test_reasoning_heuristic_gemini_2_5(self):
        caps = infer_capabilities("gemini-2.5-flash", {})
        assert caps["supports_reasoning"] is True
        assert caps["supports_thinking"] is True

    def test_reasoning_heuristic_kimi_k2(self):
        caps = infer_capabilities("kimi-k2", {})
        assert caps["supports_reasoning"] is True
        assert caps["supports_thinking"] is True

    def test_reasoning_heuristic_qwq(self):
        caps = infer_capabilities("qwq", {})
        assert caps["supports_reasoning"] is True
        assert caps["supports_thinking"] is True

    def test_tools_heuristic_chat_families(self):
        caps = infer_capabilities("llama-3.3-70b-instruct", {})
        assert caps["supports_tools"] is True
        assert caps["supports_function_calling"] is True

    def test_tools_heuristic_openrouter_o1(self):
        caps = infer_capabilities("openai/o1", {})
        assert caps["supports_tools"] is True
        assert caps["supports_function_calling"] is True

    def test_tools_heuristic_excluded_family(self):
        caps = infer_capabilities("text-embedding-3-small", {})
        assert caps["supports_tools"] is False  # embeddings excluded
        assert caps["supports_embeddings"] is True

    def test_tools_heuristic_whisper(self):
        caps = infer_capabilities("whisper-large-v3", {})
        assert caps["supports_tools"] is False  # audio excluded
        assert caps["supports_audio"] is True


class TestInferenceOfficialMetadata:
    """Test OpenRouter/HuggingFace pipeline tag metadata."""

    def test_openrouter_vision_modality(self):
        raw = {"architecture": {"modality": "text+image", "input_modalities": ["text", "image"]}}
        caps = infer_capabilities("openai/gpt-4o", raw, "openai")
        assert caps["supports_vision"] is True
        assert caps["supports_audio"] is None

    def test_openrouter_audio_modalities(self):
        raw = {"architecture": {"input_modalities": ["text", "audio"]}}
        caps = infer_capabilities("openai/whisper", raw, "openai")
        assert caps["supports_audio"] is True

    def test_huggingface_embeddings_pipeline(self):
        raw = {"pipeline_tag": "feature-extraction"}
        caps = infer_capabilities("thenlper/gte-large", raw, "huggingface")
        assert caps["supports_embeddings"] is True

    def test_huggingface_vision_tools_json(self):
        raw = {
            "pipeline_tag": "text-generation",
            "inference": {
                "chat_completion": {"tags": ["tools", "structured-output", "vision"]}
            },
        }
        caps = infer_capabilities("meta-llama/Llama-3.3-70B-Instruct", raw, "huggingface")
        assert caps["supports_tools"] is True
        assert caps["supports_function_calling"] is True
        assert caps["supports_json"] is True
        assert caps["supports_vision"] is True

    def test_huggingface_reasoning_thinking_tags(self):
        raw = {
            "pipeline_tag": "text-generation",
            "inference": {
                "chat_completion": {"tags": ["reasoning", "thinking"]}
            },
        }
        caps = infer_capabilities("meta-llama/Llama-3.3-70B-Instruct", raw, "huggingface")
        assert caps["supports_reasoning"] is True
        assert caps["supports_thinking"] is True


class TestMergeIntoModelInfo:
    """Test that merge_into_modelinfo respects explicit adapter-set values."""

    def test_merge_preserves_explicit_true(self):
        model_info = {"supports_tools": True}
        inferred = {"supports_tools": None, "supports_reasoning": True}
        merged = merge_into_modelinfo(model_info, inferred)
        assert merged["supports_tools"] is True  # preserved

    def test_merge_promotes_none_to_true(self):
        model_info = {}
        inferred = {"supports_tools": True, "supports_reasoning": True}
        merged = merge_into_modelinfo(model_info, inferred)
        assert merged["supports_tools"] is True
        assert merged["supports_reasoning"] is True


class TestReasoningRoutingCapability:
    """RouteCandidate must carry supports_thinking so reasoning category is routable."""

    def test_route_candidate_has_thinking_field(self):
        c = RouteCandidate(
            provider_type="google",
            provider_instance_id="google-1",
            model_id="gemini-2.5-flash",
            supports_reasoning=True,
            supports_thinking=True,
        )
        assert c.supports_thinking is True
        assert c.supports_reasoning is True

    def test_route_candidate_defaults_thinking_false(self):
        c = RouteCandidate(
            provider_type="google",
            provider_instance_id="google-1",
            model_id="x",
        )
        assert c.supports_thinking is False

    def test_modelinfo_thinking_flows_to_candidate(self):
        m = ModelInfo(id="gemini-2.5-flash", display_name="f", provider_id="google", provider_name="g",
                      supports_reasoning=True, supports_thinking=True)
        assert m.supports_thinking is True


class TestTokenMatchDigitBoundary:
    """Version-suffixed family names (qwen2.5, deepseek-coder) must match."""

    def test_qwen_matches_versioned_id(self):
        caps = bool_from_inference(infer_capabilities("qwen2.5-coder:7b", {}))
        assert caps["supports_tools"] is True
        assert caps["supports_function_calling"] is True

    def test_qwen_matches_plain_family(self):
        caps = bool_from_inference(infer_capabilities("qwen2.5:7b", {}))
        assert caps["supports_tools"] is True

    def test_deepseek_coder_matches(self):
        caps = bool_from_inference(infer_capabilities("deepseek-coder:6.7b", {}))
        assert caps["supports_tools"] is True

    def test_gpt_family_still_matches(self):
        caps = bool_from_inference(infer_capabilities("gpt-4o", {}))
        assert caps["supports_tools"] is True


class TestRegressionCodez: 
    """Regression test for from_old_format missing supports_tools bug."""

    def test_from_old_format_missing_supports_tools(self):
        from aios.core.model_info import ModelInfo

        model_dict = {
            "id": "gpt-4",
            "displayName": "GPT-4",
            "providerId": "openai",
            "providerName": "OpenAI",
            "contextLength": 8192,
            "maxOutput": 4096,
            "supportsStreaming": True,
            "supportsVision": False,
            "supportsReasoning": False,
            "supportsThinking": False,
            "supportsFunctionCalling": True,
            "supportsJSON": True,
            "isFree": False,
        }

        # This should NOT drop supportsFunctionCalling
        info = ModelInfo.from_old_format(model_dict, "openai", "OpenAI")
        assert info.supports_tools is True, "from_old_format should preserve supportsFunctionCalling as supports_tools"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""Centralized model capability inference for AI models.

Priority order (highest → lowest):
  1. Provider metadata — explicit `supports_*` / capability fields from the
     provider's own response. NEVER overwritten.
  2. Official model metadata — OpenRouter architecture, HuggingFace pipeline_tag
     + inference tags, documented capabilities.
  3. Centralized heuristics — high-confidence model-family markers shared across
     all adapters.
  4. Unknown (None) — NOT asserted False. Unknown remains unknown.

Heuristics only ever PROMOTE a capability to True (never assert False, except
the well-known excluded families for tool calling). Unknown stays None.

Coding capability is a derived concept: a model is "coding-suitable" based on
reasoning + tool calling + official coding families — not simply tools==coding.

All adapters MUST route capability extraction through this module; heuristics
must NOT be duplicated per-adapter.
"""

from __future__ import annotations

import re
from typing import Any

_CAPABILITY_KEYS: tuple[str, ...] = (
    "supports_reasoning", "supports_thinking", "supports_tools",
    "supports_function_calling", "supports_json", "supports_embeddings",
    "supports_vision", "supports_audio", "supports_image_generation",
    "supports_video", "supports_files",
)

_REASONING_MARKERS: tuple[str, ...] = (
    "o1", "o3", "o4", "r1", "reasoner", "reasoning", "qwq",
    "kimi-k2", "gemini-2.5", "gemini-3", "qwen3-thinking", "qwen3-reasoning",
    "glm-4.5-thinking", "glm-4.6-thinking", "claude-thinking",
)
_THINKING_MARKERS: tuple[str, ...] = ("thinking",)

_TOOL_CHAT_FAMILY: tuple[str, ...] = (
    "o1", "o3", "o4", "gpt-", "gpt4", "claude-", "gemini", "grok",
    "llama-3", "llama-2", "llama3", "qwen", "mistral", "mixtral",
    "gemma", "phi-", "deepseek-chat", "deepseek-v3", "deepseek-coder", "deepseek-r1", "kimi",
    "glm-", "command-r", "command-a", "command-", "nemotron",
    "codellama", "wizardcoder", "starcoder", "aya-", "solar", "tulu",
    "internlm", "yi-", "minicpm", "chatglm", "granite-", "nemo-",
    "gpt-oss", "bart", "flan", "bloom", "falcon",
)

_EXCLUDED_FAMILIES: tuple[str, ...] = (
    "embedding", "embed", "gte", "bge", "e5-", "jina", "rerank", "sentence",
    "whisper", "tts", "text-to-speech", "dall-e", "sdxl", "stable-diffusion",
    "flux", "imagen", "playground-v", "cogvideo", "video-gen", "wan-",
    "canary", "parakeet", "sst", "rvad", "ttv", "text-to-video",
)

_EMBEDDING_MARKERS: tuple[str, ...] = (
    "embedding", "embed", "gte", "bge", "e5", "jina", "rerank", "sentence",
    "feature-extraction",
)

_AUDIO_MARKERS: tuple[str, ...] = (
    "whisper", "tts", "text-to-speech", "parakeet", "canary", "sst", "rvad", "audio",
)

_VISION_MARKERS: tuple[str, ...] = (
    "vision", "vl", "multimodal", "llava", "gpt-4o", "gpt-4-turbo", "claude-3",
    "claude-sonnet-4", "claude-opus-4", "gemini", "idefics", "fuyu", "qwen-vl",
)

_IMAGE_GEN_MARKERS: tuple[str, ...] = (
    "dall-e", "stable-diffusion", "sdxl", "flux", "imagegen", "imagen",
    "playground-v", "deepfloyd", "wan-2", "sana", "text-to-image", "text2img",
)

_VIDEO_MARKERS: tuple[str, ...] = (
    "video-gen", "cogvideo", "wan-", "text-to-video", "text2video", "veo", "sora",
    "moviegen",
)

_FILES_MARKERS: tuple[str, ...] = ("document", "file-input", "pdf", "docs")


def _truthy(*values: Any) -> bool | None:
    """Return True if any value is truthy, otherwise None (unknown)."""
    for v in values:
        if v is True:
            return True
        if isinstance(v, str) and v.strip().lower() in ("true", "yes", "1"):
            return True
    return None


def _meta_flag(raw: dict, *keys: str) -> bool | None:
    """Extract an explicit provider metadata flag as True/False/None.

    If any of ``keys`` is present, return its truthiness (True for truthy
    values, False for falsy). An explicit ``False`` is preserved — it is NOT
    collapsed to unknown. If none of the keys are present, return None.
    """
    present = False
    for k in keys:
        if k in raw:
            present = True
            v = raw[k]
            if v is True:
                return True
            if isinstance(v, str) and v.strip().lower() in ("true", "yes", "1"):
                return True
            if isinstance(v, dict):
                return True
            if isinstance(v, (list, tuple)) and len(v) > 0:
                return True
    return False if present else None


def _token_match(model_id_lower: str, markers: tuple[str, ...]) -> bool:
    """Match a marker as a delimited token (start/end or `-/_/.:` boundaries).

    Leading/trailing delimiters on markers are stripped so that family prefixes
    like ``gpt-`` match ``gpt-4o`` while ``o1`` still matches the bare id ``o1``.

    A digit is also accepted as a right boundary so that family names with
    version suffixes (e.g. ``qwen`` in ``qwen2.5-coder:7b``) still match.
    """
    for marker in markers:
        if marker == "o1" and "gpt-4o" in model_id_lower:
            continue
        tok = marker.strip("-/._:")
        if not tok:
            continue
        if re.search(rf'(^|[-/._:]){re.escape(tok)}([-/._:]|[0-9]|$)', model_id_lower):
            return True
    return False


def _promote(flags: dict[str, bool | None], key: str) -> None:
    """Set a capability to True, but never overwrite an explicit value."""
    if flags.get(key) is None:
        flags[key] = True


def infer_capabilities(model_id: str, raw: dict, provider_type: str = "") -> dict[str, bool | None]:
    """
    Infer model capabilities with tri-state (True/False/None).

    Returns a dict keyed by ``_CAPABILITY_KEYS``. ``None`` means unknown.

    Priority:
        1. Explicit provider metadata (never overwritten)
        2. Official metadata (OpenRouter/HuggingFace)
        3. ID heuristics (promote-only)
        4. Unknown (None)
    """
    low = model_id.lower()
    flags: dict[str, bool | None] = {k: None for k in _CAPABILITY_KEYS}

    # --- 1. Explicit provider metadata (highest priority) ---
    reasoning = _meta_flag(
        raw, "supports_reasoning", "reasoning", "reasoning_model",
        "reasoning_effort", "chain_of_thought", "chainOfThought",
    )
    thinking = _meta_flag(
        raw, "supports_thinking", "thinking", "chain_of_thought", "chainOfThought",
    )
    fc = _meta_flag(
        raw, "supports_function_calling", "function_calling",
        "functionCalling", "supports_functions", "tool_calls", "toolCalling",
    )
    tools = _meta_flag(
        raw, "supports_tools", "tool_use", "tools",
    )
    json_cap = _meta_flag(
        raw, "supports_json", "json_mode", "structured_output",
        "structuredOutput", "response_format", "json_schema",
    )
    embeddings = _meta_flag(
        raw, "supports_embeddings", "embedding", "embeddings", "feature_extraction",
    )
    vision = _meta_flag(
        raw, "supports_vision", "vision", "image_input", "imageInput",
    )
    audio = _meta_flag(
        raw, "supports_audio", "audio", "audio_input", "audioInput",
    )
    image_gen = _meta_flag(
        raw, "supports_image_generation", "image_generation",
        "imageGeneration", "text_to_image",
    )
    video = _meta_flag(
        raw, "supports_video", "video", "video_input", "videoInput",
    )
    files = _meta_flag(
        raw, "supports_files", "file_input", "files", "fileInput",
    )

    if reasoning is not None:
        flags["supports_reasoning"] = reasoning
    if thinking is not None:
        flags["supports_thinking"] = thinking
    if fc is not None:
        flags["supports_function_calling"] = fc
    if tools is not None:
        flags["supports_tools"] = tools
    if json_cap is not None:
        flags["supports_json"] = json_cap
    if embeddings is not None:
        flags["supports_embeddings"] = embeddings
    if vision is not None:
        flags["supports_vision"] = vision
    if audio is not None:
        flags["supports_audio"] = audio
    if image_gen is not None:
        flags["supports_image_generation"] = image_gen
    if video is not None:
        flags["supports_video"] = video
    if files is not None:
        flags["supports_files"] = files

    # --- 2. Official model metadata (promote-only) ---
    arch = raw.get("architecture", {})
    if isinstance(arch, dict):
        modality = str(arch.get("modality", "")).lower()
        in_mod = arch.get("input_modalities")
        mods = {str(x).lower() for x in in_mod} if isinstance(in_mod, list) else set()
        if modality:
            if "image" in modality:
                _promote(flags, "supports_vision")
            if "audio" in modality:
                _promote(flags, "supports_audio")
            if "video" in modality:
                _promote(flags, "supports_video")
        if "image" in mods:
            _promote(flags, "supports_vision")
        if "audio" in mods:
            _promote(flags, "supports_audio")
        if "video" in mods:
            _promote(flags, "supports_video")

    pt = str(raw.get("pipeline_tag", "")).lower()
    if pt:
        if pt in ("feature-extraction", "sentence-similarity", "text-embeddings", "fill-mask"):
            _promote(flags, "supports_embeddings")
        if pt in ("image-classification", "image-to-text", "object-detection",
                  "visual-question-answering", "image-segmentation", "depth-estimation",
                  "image-text-to-text"):
            _promote(flags, "supports_vision")
        if pt in ("text-to-image", "image-to-image", "text-to-svg", "stable-diffusion",
                  "image-generation", "text-to-3d"):
            _promote(flags, "supports_image_generation")
        if pt in ("text-to-speech", "text-to-audio", "automatic-speech-recognition",
                  "audio-to-audio", "speech-to-text", "audio-classification"):
            _promote(flags, "supports_audio")
        if pt in ("text-to-video", "video-to-text", "image-to-video"):
            _promote(flags, "supports_video")

        inference = raw.get("inference", {})
        if isinstance(inference, dict):
            for _pipeline, cfg in inference.items():
                if not isinstance(cfg, dict):
                    continue
                tags = cfg.get("tags", [])
                if not isinstance(tags, list):
                    continue
                tag_low = {str(t).lower() for t in tags}
                if "tools" in tag_low or "function-calling" in tag_low:
                    _promote(flags, "supports_tools")
                    _promote(flags, "supports_function_calling")
                if "structured-output" in tag_low or "json" in tag_low:
                    _promote(flags, "supports_json")
                if "reasoning" in tag_low or "thinking" in tag_low:
                    _promote(flags, "supports_reasoning")
                    _promote(flags, "supports_thinking")
                if "vision" in tag_low or "image" in tag_low:
                    _promote(flags, "supports_vision")
                if "audio" in tag_low:
                    _promote(flags, "supports_audio")
                if "video" in tag_low:
                    _promote(flags, "supports_video")
                if "document" in tag_low or "file" in tag_low:
                    _promote(flags, "supports_files")

    # --- 3. Centralized ID heuristics (promote-only) ---
    if _token_match(low, _REASONING_MARKERS):
        _promote(flags, "supports_reasoning")
        _promote(flags, "supports_thinking")
    if _token_match(low, _THINKING_MARKERS):
        _promote(flags, "supports_thinking")
        _promote(flags, "supports_reasoning")
    if _token_match(low, _TOOL_CHAT_FAMILY):
        _promote(flags, "supports_tools")
        _promote(flags, "supports_function_calling")
    if _token_match(low, _EXCLUDED_FAMILIES) and flags["supports_tools"] is None:
        flags["supports_tools"] = False
    if _token_match(low, _EMBEDDING_MARKERS):
        _promote(flags, "supports_embeddings")
    if _token_match(low, _AUDIO_MARKERS):
        _promote(flags, "supports_audio")
    if _token_match(low, _VISION_MARKERS):
        _promote(flags, "supports_vision")
    if _token_match(low, _IMAGE_GEN_MARKERS):
        _promote(flags, "supports_image_generation")
    if _token_match(low, _VIDEO_MARKERS):
        _promote(flags, "supports_video")
    if _token_match(low, _FILES_MARKERS):
        _promote(flags, "supports_files")

    # Derived: explicit function-calling implies tool support (and vice versa),
    # but only when the other is still unknown.
    if flags["supports_function_calling"] is True and flags["supports_tools"] is None:
        flags["supports_tools"] = True
    if flags["supports_tools"] is True and flags["supports_function_calling"] is None:
        flags["supports_function_calling"] = True

    return flags


def bool_from_inference(flags: dict[str, bool | None]) -> dict[str, bool]:
    """Map tri-state inference (True/False/None) to boolean for ModelInfo compat."""
    return {k: v is True for k, v in flags.items()}


def merge_into_modelinfo(model_info: dict, inferred: dict[str, bool | None]) -> dict:
    """Merge inferred capabilities into a model dict, respecting explicit values.

    Existing ``True``/``False`` values in ``model_info`` are never overwritten.
    Unknown (None) inferred values are left untouched.
    """
    for k, v in inferred.items():
        current = model_info.get(k)
        if current is True or current is False:
            continue
        if v is True:
            model_info[k] = True
    return model_info


__all__ = ["infer_capabilities", "bool_from_inference", "merge_into_modelinfo"]

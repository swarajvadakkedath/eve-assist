"""W2 live validation harness — reasoning + coding category routing.

Loads the real onboarded providers (~/.eve), refreshes models from the live
APIs using the fixed capability inference, then verifies that:
  - reasoning models (o1/o3/r1/deepseek/gemini-2.5/kimi/qwq) carry
    supports_reasoning + supports_thinking
  - coding models carry tools + function_calling (+ reasoning where relevant)
  - SmartRouter.category route() resolves for reasoning / coding
  - no model with an explicit provider False loses that flag
"""

import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend"))

from aios.core.provider_manager import ProviderManager
from aios.core.smart_router import SmartRouter, RoutingPolicy
from aios.core.health_monitor import HealthMonitor
from aios.core.capability_inference import infer_capabilities

REASONING_IDS = [
    "o1", "o3-mini", "deepseek-r1", "deepseek-reasoner",
    "gemini-2.5-flash", "gemini-2.5-pro", "kimi-k2", "qwq",
]
CODING_IDS = [
    "gpt-4o", "claude-sonnet-4-20250514", "llama-3.3-70b-instruct",
    "deepseek-chat", "qwen2.5-coder", "gpt-4-turbo",
]


def summarize_models(models):
    reasoning = [m for m in models if m.get("supportsReasoning") and m.get("supportsThinking")]
    thinking_only = [m for m in models if not m.get("supportsReasoning") and m.get("supportsThinking")]
    reasoning_no_think = [m for m in models if m.get("supportsReasoning") and not m.get("supportsThinking")]
    tools = [m for m in models if m.get("supportsTools")]
    fc = [m for m in models if m.get("supportsFunctionCalling")]
    coding = [m for m in models if m.get("supportsTools") and m.get("supportsFunctionCalling")]
    return {
        "total": len(models),
        "reasoning+thinking": len(reasoning),
        "thinking_only": len(thinking_only),
        "reasoning_no_thinking": len(reasoning_no_think),
        "tools": len(tools),
        "function_calling": len(fc),
        "coding(tools+fc)": len(coding),
        "examples_reasoning": [m["id"] for m in reasoning[:6]],
        "examples_coding": [m["id"] for m in coding[:6]],
    }


def main():
    config_dir = os.path.expanduser("~/.eve")
    if not os.path.exists(os.path.join(config_dir, "providers.json")):
        print("SKIP: no providers.json at ~/.eve — cannot run live validation")
        return 0

    health = HealthMonitor()
    router = SmartRouter(health_monitor=health)
    manager = ProviderManager(
        config_dir=config_dir,
        smart_router=router,
        health_monitor=health,
    )
    manager.register_all_adapters()

    # Refresh models from live APIs (concurrency 4) — exercises fixed inference.
    print("Refreshing models from live APIs (concurrency=4)...")
    results = asyncio.run(manager.refresh_all_models(concurrency_limit=4))

    all_models = [m for pid in results for m in results[pid]]
    print(f"\n=== Model counts by provider ===")
    for pid, models in results.items():
        print(f"  {pid:32s} {len(models):4d}")

    print("\n=== Capability summary (all providers) ===")
    summary = summarize_models(all_models)
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # -- Verify reasoning IDs carry reasoning + thinking (via live data) ---
    print("\n=== Reasoning ID spot-check ===")
    for rid in REASONING_IDS:
        hits = [m for m in all_models if m["id"] == rid or m["id"].endswith(rid)]
        if not hits:
            print(f"  {rid:24s} NOT FOUND in live models")
            continue
        for h in hits:
            print(
                f"  {h['id']:40s} reasoning={h.get('supportsReasoning')} "
                f"thinking={h.get('supportsThinking')} tools={h.get('supportsTools')}"
            )

    # -- Verify coding IDs carry tools + fc ---------------------------------
    print("\n=== Coding ID spot-check ===")
    for cid in CODING_IDS:
        hits = [m for m in all_models if m["id"] == cid or m["id"].endswith(cid) or cid in m["id"]]
        if not hits:
            print(f"  {cid:40s} NOT FOUND in live models")
            continue
        for h in hits[:2]:
            print(
                f"  {h['id']:40s} tools={h.get('supportsTools')} "
                f"fc={h.get('supportsFunctionCalling')} reasoning={h.get('supportsReasoning')}"
            )

    # -- Routing resolution: reasoning + coding categories ------------------
    print("\n=== SmartRouter category routing (live, AUTO, FREE_ONLY) ===")
    for category in ("reasoning", "coding", "general_chat"):
        try:
            req = type("Req", (), {"messages": [], "model": "", "max_tokens": 256,
                                   "temperature": 0.7, "top_p": 1.0, "tools": None,
                                   "stream": False, "stop": None, "provider_id": None})()
            result = asyncio.run(router._resolve_route(
                router._to_chat_request(req), category,
                RoutingPolicy.AUTO, None, streaming=False,
            ))
            cand = result.candidate
            print(f"  {category:12s} -> {cand.provider_type}/{cand.model_id} "
                  f"(capabilities: reasoning={cand.supports_reasoning} "
                  f"thinking={cand.supports_thinking} tools={cand.supports_tools} "
                  f"fc={cand.supports_function_calling})")
        except Exception as e:
            print(f"  {category:12s} -> ERROR: {type(e).__name__}: {e}")

    # -- Direct unit check: explicit False preserved in inference ------------
    print("\n=== Inference tri-state sanity ===")
    for mid in ("deepseek-reasoner", "o3-mini", "plain-random", "text-embedding-3-small"):
        caps = infer_capabilities(mid, {})
        print(f"  {mid:28s} reasoning={caps['supports_reasoning']} thinking={caps['supports_thinking']} "
              f"tools={caps['supports_tools']}")
    caps = infer_capabilities("deepseek-reasoner", {"supports_thinking": False, "supports_reasoning": False})
    print(f"  {'explicit-False-model':28s} reasoning={caps['supports_reasoning']} "
          f"thinking={caps['supports_thinking']} (must stay False, not promoted)")

    print("\nLIVE_VALIDATION_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

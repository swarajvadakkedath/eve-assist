"""Tests for W7 — parallel model discovery + background refresh."""

import asyncio
import json

import pytest

from aios.core.provider_manager import ProviderManager
from aios.core.cache import ModelCache


class CountingAdapter:
    """Adapter that returns a per-call model list and counts invocations."""

    def __init__(self, model_ids, provider_id="p"):
        self._model_ids = model_ids
        self._provider_id = provider_id
        self.calls = 0
        self._latency = 0.0

    @property
    def provider_id(self):
        return self._provider_id

    async def list_models(self):
        self.calls += 1
        if self._latency:
            await asyncio.sleep(self._latency)
        from aios.core.model_info import ModelInfo

        return [ModelInfo(id=mid, display_name=mid, provider_id=self._provider_id, provider_name=self._provider_id) for mid in self._model_ids]


@pytest.fixture
def manager_factory(tmp_path):
    def make(providers):
        (tmp_path / "providers.json").write_text(json.dumps(providers), "utf-8")
        (tmp_path / "routing.json").write_text(json.dumps([]), "utf-8")
        m = ProviderManager(config_dir=str(tmp_path))
        return m, tmp_path
    return make


class TestParallelDiscovery:
    async def test_refresh_all_models_fetches_each_provider(self, manager_factory):
        providers = [
            {"id": "p1", "type": "openai", "name": "P1", "models": [], "enabled": True},
            {"id": "p2", "type": "groq", "name": "P2", "models": [], "enabled": True},
            {"id": "p3", "type": "ollama", "name": "P3", "models": [], "enabled": True},
        ]
        m, tmp_path = manager_factory(providers)
        m._adapters = {
            "p1": CountingAdapter(["a", "b"], "p1"),
            "p2": CountingAdapter(["c"], "p2"),
            "p3": CountingAdapter([], "p3"),
        }

        results = await m.refresh_all_models(concurrency_limit=2)
        assert set(results.keys()) == {"p1", "p2", "p3"}
        assert {"a", "b"}.issubset({x["id"] for x in results["p1"]})
        assert {"c"}.issubset({x["id"] for x in results["p2"]})
        assert isinstance(results["p3"], list)

    async def test_refresh_all_persists_and_syncs_router(self, manager_factory):
        providers = [
            {"id": "p1", "type": "openai", "name": "P1", "models": [], "enabled": True},
        ]
        m, tmp_path = manager_factory(providers)
        m._adapters = {"p1": CountingAdapter(["m1", "m2"], "p1")}

        await m.refresh_all_models()
        saved = json.loads((tmp_path / "providers.json").read_text("utf-8"))
        model_ids = {x["id"] for x in saved[0]["models"]}
        assert {"m1", "m2"}.issubset(model_ids)

    async def test_failure_in_one_provider_does_not_block_others(self, manager_factory):
        providers = [
            {"id": "p1", "type": "openai", "name": "P1", "models": [], "enabled": True},
            {"id": "p2", "type": "groq", "name": "P2", "models": [], "enabled": True},
        ]
        m, tmp_path = manager_factory(providers)

        class BoomAdapter:
            @property
            def provider_id(self):
                return "boom"

            async def list_models(self):
                raise RuntimeError("boom")

        m._adapters = {"p1": CountingAdapter(["x"], "p1"), "p2": BoomAdapter()}
        results = await m.refresh_all_models()
        assert {"x"}.issubset({x["id"] for x in results["p1"]})
        assert "p2" in results

    async def test_parallelism_bounds_concurrency(self, manager_factory):
        providers = [
            {"id": f"p{i}", "type": "openai", "name": f"P{i}", "models": [], "enabled": True}
            for i in range(6)
        ]
        m, tmp_path = manager_factory(providers)
        adapters = {p["id"]: CountingAdapter([], p["id"]) for p in providers}
        for a in adapters.values():
            a._latency = 0.05
        m._adapters = adapters

        start = asyncio.get_event_loop().time()
        await m.refresh_all_models(concurrency_limit=2)
        elapsed = asyncio.get_event_loop().time() - start
        # 6 providers / 2 concurrency * 50ms ≈ 150ms minimum; sequential would be ~300ms.
        assert elapsed < 0.30


class TestBackgroundRefresh:
    async def test_start_and_stop_background_refresh(self, manager_factory):
        providers = [
            {"id": "p1", "type": "openai", "name": "P1", "models": [], "enabled": True},
        ]
        m, tmp_path = manager_factory(providers)
        adapter = CountingAdapter(["a", "b"], "p1")
        m._adapters = {"p1": adapter}

        m.start_background_refresh(interval=0.05, concurrency_limit=1)
        assert m.is_background_refresh_running()

        await asyncio.sleep(0.3)
        assert adapter.calls >= 2
        saved = json.loads((tmp_path / "providers.json").read_text("utf-8"))
        assert {"a", "b"}.issubset({x["id"] for x in saved[0]["models"]})

        m.stop_background_refresh()
        assert not m.is_background_refresh_running()

    async def test_start_is_idempotent(self, manager_factory):
        providers = [{"id": "p1", "type": "openai", "name": "P1", "models": [], "enabled": True}]
        m, tmp_path = manager_factory(providers)
        m._adapters = {"p1": CountingAdapter([], "p1")}
        m.start_background_refresh(interval=10)
        m.start_background_refresh(interval=10)
        await m.shutdown()

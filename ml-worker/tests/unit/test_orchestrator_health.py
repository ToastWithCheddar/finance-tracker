"""Section F (ML-PR-001): the ProductionOrchestrator must expose a cheap
`health()` payload and must be constructible/initializable without model
weights when ML_PROD_REQUIRE_WEIGHTS=0 (degraded mode).
"""

from __future__ import annotations

import asyncio
import os

import pytest


@pytest.fixture(autouse=True)
def _no_weights_env(monkeypatch):
    monkeypatch.setenv("ML_PROD_REQUIRE_WEIGHTS", "0")
    # Avoid real prometheus binding side effects in case orchestrator loads.
    monkeypatch.setenv("ML_METRICS_PORT", "0")
    yield


def test_orchestrator_constructs_with_no_args():
    from production_orchestrator import ProductionOrchestrator
    orch = ProductionOrchestrator()
    payload = orch.health()
    assert set(payload.keys()) >= {
        "initialized",
        "onnx_loaded",
        "prototypes_loaded",
        "cache_size",
    }
    # Pre-init: not initialized, no ONNX, no prototypes.
    assert payload["initialized"] is False
    assert payload["onnx_loaded"] is False


def test_initialize_production_does_not_crash_without_weights(monkeypatch):
    from production_orchestrator import ProductionOrchestrator

    orch = ProductionOrchestrator()

    # Force _setup_models to behave as if weights are missing.
    async def _boom():
        raise FileNotFoundError("simulated missing weights")

    monkeypatch.setattr(orch, "_setup_models", _boom)
    # Disable monitoring so we don't bind a port.
    orch.model_monitor = None

    # With ML_PROD_REQUIRE_WEIGHTS=0 we expect graceful degradation.
    asyncio.run(orch.initialize_production())

    h = orch.health()
    assert h["initialized"] is True  # init *completed*, just degraded
    assert h["production_ready"] is False


def test_initialize_production_raises_when_weights_required(monkeypatch):
    from production_orchestrator import ProductionOrchestrator

    monkeypatch.setenv("ML_PROD_REQUIRE_WEIGHTS", "1")
    orch = ProductionOrchestrator()

    async def _boom():
        raise FileNotFoundError("simulated missing weights")

    monkeypatch.setattr(orch, "_setup_models", _boom)
    orch.model_monitor = None

    with pytest.raises(FileNotFoundError):
        asyncio.run(orch.initialize_production())
    assert orch.is_initialized is False

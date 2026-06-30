"""Shared pytest fixtures.

Loads each service's main.py (all named main.py) under a unique module name,
isolates the failure store and circuit breaker registry per test, and provides
fake cross-service clients.
"""

import importlib.util
import os
import pathlib
import sys

import pytest
from autosre_shared import ServiceClient

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Configure the platform for tests BEFORE any service module is imported.
os.environ.setdefault("FAILURE_LOG_PATH", str(ROOT / ".pytest_failures.jsonl"))
os.environ["RATE_LIMIT_RPS"] = "1000"  # avoid the limiter interfering
os.environ["RATE_LIMIT_BURST"] = "1000"
os.environ["WORKER_INTERVAL"] = "0.05"
os.environ["WORKER_JOB_SECONDS"] = "0.01"
os.environ["AUTH_DEP_LATENCY"] = "0.01"


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def api_module():
    return _load("api_main", "api/main.py")


@pytest.fixture(scope="session")
def auth_module():
    return _load("auth_main", "auth/main.py")


@pytest.fixture(scope="session")
def worker_module():
    return _load("worker_main", "worker/main.py")


def _reset_chaos(ctrl):
    s = ctrl.state
    s.latency_enabled = False
    s.latency_seconds = 0.0
    s.error_enabled = False
    s.error_rate = 0.0
    s._error_accumulator = 0.0
    s._memory_blocks.clear()
    s.memory_bytes = 0


@pytest.fixture(autouse=True)
def _isolate(tmp_path_factory):
    """Each test gets a fresh failure store; registry + chaos reset after."""
    from autosre_shared.storage import failure_store

    path = tmp_path_factory.mktemp("fs") / "failures.jsonl"
    failure_store.set_failure_store(failure_store.FileFailureStore(str(path)))
    yield
    from autosre_shared.resilience import reset_registry

    reset_registry()
    for name in ("api_main", "auth_main", "worker_main"):
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "app"):
            _reset_chaos(mod.app.state.chaos)


# --- fake cross-service clients (dependency abstraction) ---
class _FakeOK(ServiceClient):
    async def get_json(self, path, **kw):
        return {}

    async def post_json(self, path, json=None, **kw):
        return {"valid": True}


class _FakeInvalid(ServiceClient):
    async def get_json(self, path, **kw):
        return {}

    async def post_json(self, path, json=None, **kw):
        return {"valid": False}


class _FakeDown(ServiceClient):
    async def get_json(self, path, **kw):
        raise RuntimeError("dependency down")

    async def post_json(self, path, json=None, **kw):
        raise RuntimeError("dependency down")


@pytest.fixture
def fake_auth_ok():
    return _FakeOK()


@pytest.fixture
def fake_auth_invalid():
    return _FakeInvalid()


@pytest.fixture
def fake_auth_down():
    return _FakeDown()

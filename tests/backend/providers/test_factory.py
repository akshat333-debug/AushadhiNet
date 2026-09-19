"""DoD test for backend/providers/factory.py (step 25)."""
from __future__ import annotations

import sys

import pytest

from backend.providers.factory import get


@pytest.fixture(autouse=True)
def _clear_cache():
    get.cache_clear()
    yield
    get.cache_clear()


def test_local_mode_returns_local_provider(monkeypatch):
    monkeypatch.setattr("backend.providers.factory.get_settings", lambda: type("S", (), {"mode": "local", "duckdb_path": ":memory:", "signing_key": "k"})())
    from backend.providers.speech_local import LocalSpeechProvider
    provider = get("speech")
    assert isinstance(provider, LocalSpeechProvider)


def test_local_mode_never_imports_google_sdk(monkeypatch):
    """The single most important assertion here: local mode must not even
    import google.cloud.* modules, let alone construct a client."""
    monkeypatch.setattr("backend.providers.factory.get_settings", lambda: type("S", (), {"mode": "local", "duckdb_path": ":memory:", "signing_key": "k"})())
    blocked = [m for m in list(sys.modules) if m.startswith("google.cloud") or m.startswith("google.genai")]
    for m in blocked:
        monkeypatch.delitem(sys.modules, m)  # restored after the test; a permanent delete re-registers protobufs on the next import

    for name in ("speech", "llm", "embed", "translate", "tts", "store_live", "store_history", "queue", "sign", "messaging", "routes"):
        get(name)

    still_absent = [m for m in sys.modules if m.startswith("google.cloud") or m.startswith("google.genai")]
    assert still_absent == [], f"local mode imported Google SDK modules: {still_absent}"


def test_get_is_memoised(monkeypatch):
    monkeypatch.setattr("backend.providers.factory.get_settings", lambda: type("S", (), {"mode": "local", "duckdb_path": ":memory:", "signing_key": "k"})())
    a = get("queue")
    b = get("queue")
    assert a is b


def test_unknown_provider_name_raises():
    with pytest.raises(KeyError):
        get("not-a-real-provider")


def test_unknown_mode_raises(monkeypatch):
    monkeypatch.setattr("backend.providers.factory.get_settings", lambda: type("S", (), {"mode": "chaos"})())
    with pytest.raises(ValueError):
        get("queue")

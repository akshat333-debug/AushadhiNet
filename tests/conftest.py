"""Repo-wide test isolation (found via a real bug: tests/backend/api/test_worker.py
was accumulating rows across runs because backend.config.get_settings() and
backend.providers.factory.get() are process-wide memoised singletons --
architecture.md §2's factory pattern is correct for production, but a test
suite needs a fresh provider set per test, not one shared singleton for the
whole pytest process).
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_singleton_caches():
    from backend.config import get_settings
    from backend.providers.factory import get as factory_get

    get_settings.cache_clear()
    factory_get.cache_clear()
    yield
    get_settings.cache_clear()
    factory_get.cache_clear()

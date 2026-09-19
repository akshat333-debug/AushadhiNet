"""Local route provider (modular-plan.md §2.2): reuses
ml.data.graph.HaversineProvider, which already implements exactly this
protocol (great-circle distance / assumed rural speed) -- no need to
reimplement it here (ponytail: reuse over duplication)."""
from __future__ import annotations

from ml.data.graph import HaversineProvider as LocalRouteProvider

__all__ = ["LocalRouteProvider"]

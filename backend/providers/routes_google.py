"""Google Maps Routes API provider (architecture.md §1) -- real drive
times, replacing the Haversine estimate used in local mode."""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import ProviderError


class GoogleRouteProvider:
    def __init__(self):
        self._api_key = get_settings().maps_api_key

    def drive_minutes(self, a, b) -> float:
        import requests

        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {"X-Goog-Api-Key": self._api_key, "X-Goog-FieldMask": "routes.duration"}
        body = {
            "origin": {"location": {"latLng": {"latitude": a.lat, "longitude": a.lon}}},
            "destination": {"location": {"latLng": {"latitude": b.lat, "longitude": b.lon}}},
            "travelMode": "DRIVE",
        }
        try:
            response = requests.post(url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Maps Routes API failed: {e}") from e
        duration_seconds = int(data["routes"][0]["duration"].rstrip("s"))
        return duration_seconds / 60.0

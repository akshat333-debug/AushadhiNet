"""Firestore live-state store (architecture.md §1)."""
from __future__ import annotations

from typing import Callable

from pydantic import BaseModel

from backend.config import get_settings
from backend.providers.base import ProviderError


def _collection_models() -> dict[str, type[BaseModel]]:
    """Firestore stores plain JSON; callers expect the same models the local store returns."""
    from backend.domain import AuditEvent, BedCensus, CheckIn, Contact, Facility, StockRecord, TransferOrder
    return {
        "audit_events": AuditEvent, "bed_census": BedCensus, "checkins": CheckIn, "contacts": Contact,
        "facilities": Facility, "orders": TransferOrder, "stock_records": StockRecord,
    }


def _to_model(collection: str, data: dict | None):
    if data is None:
        return None
    model = _collection_models().get(collection)
    return model.model_validate(data) if model else data


class GoogleLiveStore:
    def __init__(self):
        from google.cloud import firestore

        self._client = firestore.Client(project=get_settings().gcp_project)

    def put(self, collection: str, doc_id: str, model: BaseModel) -> None:
        try:
            self._client.collection(collection).document(doc_id).set(model.model_dump(mode="json"))
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Firestore write failed: {e}") from e

    def get(self, collection: str, doc_id: str):
        snap = self._client.collection(collection).document(doc_id).get()
        return _to_model(collection, snap.to_dict()) if snap.exists else None

    def query(self, collection: str, filters: dict) -> list:
        query = self._client.collection(collection)
        for field, value in filters.items():
            query = query.where(field, "==", getattr(value, "value", value))  # enums are stored as their string value
        return [_to_model(collection, doc.to_dict()) for doc in query.stream()]

    def watch(self, collection: str, callback: Callable) -> Callable:
        def on_snapshot(col_snapshot, changes, read_time):
            for change in changes:
                callback(change.document.id, _to_model(collection, change.document.to_dict()))

        watch = self._client.collection(collection).on_snapshot(on_snapshot)
        return watch.unsubscribe

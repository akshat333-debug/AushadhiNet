"""Local live-state store (modular-plan.md §2.2): an in-process, in-memory
store, standing in for the Firestore emulator. Good enough for tests and a
single-process demo; a real emulator/Firestore is required for anything
multi-process (architecture.md §2's two-implementation seam is exactly
what makes that swap a config change, not a rewrite).
"""
from __future__ import annotations

from pydantic import BaseModel


class LocalLiveStore:
    def __init__(self):
        self._data: dict[str, dict[str, BaseModel]] = {}

    def put_many(self, collection: str, items: dict[str, BaseModel]) -> None:
        for doc_id, model in items.items():
            self.put(collection, doc_id, model)

    def put(self, collection: str, doc_id: str, model: BaseModel) -> None:
        self._data.setdefault(collection, {})[doc_id] = model

    def get(self, collection: str, doc_id: str):
        return self._data.get(collection, {}).get(doc_id)

    def query(self, collection: str, filters: dict) -> list:
        results = []
        for doc in self._data.get(collection, {}).values():
            if all(getattr(doc, k, None) == v for k, v in filters.items()):
                results.append(doc)
        return results

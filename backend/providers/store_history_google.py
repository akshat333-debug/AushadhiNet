"""BigQuery history store (architecture.md §1). `sql()` only accepts
parameterised queries (architecture.md §6) via BigQuery's named/positional
query parameters -- never raw string interpolation.
"""
from __future__ import annotations

import json

from backend.config import get_settings
from backend.providers.base import ProviderError


class GoogleHistoryStore:
    def __init__(self):
        from google.cloud import bigquery

        settings = get_settings()
        self._client = bigquery.Client(project=settings.bigquery_project)
        self._dataset = f"{settings.bigquery_project}.{settings.bigquery_dataset}"
        self._bigquery = bigquery

    def insert(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        # Nested values (e.g. confidence) go into STRING columns as JSON.
        flat = [{k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in rows]
        try:
            errors = self._client.insert_rows_json(f"{self._dataset}.{table}", flat)
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"BigQuery insert failed: {e}") from e
        if errors:
            raise ProviderError(f"BigQuery insert failed: {errors}")

    def sql(self, query: str, params: tuple | None = None) -> list[dict]:
        bigquery = self._bigquery
        query_params = [
            bigquery.ScalarQueryParameter(None, "STRING" if isinstance(p, str) else "FLOAT64", p)
            for p in (params or [])
        ]
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        try:
            result = self._client.query(query, job_config=job_config).result()
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"BigQuery query failed: {e}") from e
        return [dict(row) for row in result]

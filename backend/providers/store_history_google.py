"""BigQuery history store (architecture.md §1). `sql()` only accepts
parameterised queries (architecture.md §6) via BigQuery's named/positional
query parameters -- never raw string interpolation.
"""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import ProviderError


class GoogleHistoryStore:
    def __init__(self):
        from google.cloud import bigquery

        self._client = bigquery.Client(project=get_settings().bigquery_project)
        self._bigquery = bigquery

    def insert(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        errors = self._client.insert_rows_json(table, rows)
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

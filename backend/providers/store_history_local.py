"""Local history store (modular-plan.md §2.2): DuckDB, standing in for
BigQuery. `sql()` is parameterised-only (architecture.md §6) -- it never
accepts a pre-formatted query string with values already interpolated.
"""
from __future__ import annotations

import pathlib

import duckdb

from backend.providers.base import ProviderError


class LocalHistoryStore:
    def __init__(self, db_path: str | pathlib.Path = ":memory:"):
        self._conn = duckdb.connect(str(db_path))

    def insert(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        import pandas as pd
        df = pd.DataFrame(rows)
        self._conn.register("_tmp_insert", df)
        existing = self._conn.execute(
            "select table_name from information_schema.tables where table_name = ?", [table]
        ).fetchall()
        if not existing:
            self._conn.execute(f"create table {table} as select * from _tmp_insert limit 0")
        self._conn.execute(f"insert into {table} select * from _tmp_insert")
        self._conn.unregister("_tmp_insert")

    def sql(self, query: str, params: tuple | None = None) -> list[dict]:
        try:
            result = self._conn.execute(query, params or [])
        except duckdb.Error as e:
            raise ProviderError(f"query failed: {e}") from e
        cols = [d[0] for d in result.description]
        return [dict(zip(cols, row)) for row in result.fetchall()]

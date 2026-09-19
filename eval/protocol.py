"""Typed, read-only loader for eval/protocol.lock.

Nothing in this module writes to the lock file. ml/ and eval/ code must load
the protocol through here rather than parsing YAML themselves, so there is
exactly one place that defines what "the frozen window" means.
"""
from __future__ import annotations

import functools
import pathlib
from datetime import date

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

DEFAULT_LOCK_PATH = pathlib.Path(__file__).resolve().parent / "protocol.lock"


def _parse_month(value: str) -> date:
    year, month = value.split("-")
    return date(int(year), int(month), 1)


class RealBenchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grain: str
    source: str
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date
    excluded_months: list[str]
    held_out_district: str
    held_out_district_state: str

    @field_validator(
        "train_start", "train_end", "validation_start", "validation_end",
        "test_start", "test_end", mode="before",
    )
    @classmethod
    def _month(cls, v):
        return _parse_month(v) if isinstance(v, str) else v


class FederatedBenchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    held_out_state: str
    client_states: list[str]


class SyntheticBenchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grain: str
    test_weeks: int
    held_out_block: str


class Pilot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    district: str
    state: str


class GeneratorSeal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int
    content_hash: str | None = None
    sealed_at: str | None = None


class Protocol(BaseModel):
    """The whole frozen evaluation protocol. Extra keys are rejected so a
    typo or an unreviewed addition to protocol.lock fails loudly."""

    model_config = ConfigDict(extra="forbid")

    version: int
    real_benchmark: RealBenchmark
    federated_benchmark: FederatedBenchmark
    synthetic_benchmark: SyntheticBenchmark
    pilot: Pilot
    generator_seal: GeneratorSeal


@functools.lru_cache(maxsize=8)
def _load_cached(path_str: str) -> Protocol:
    path = pathlib.Path(path_str)
    raw = yaml.safe_load(path.read_text())
    return Protocol.model_validate(raw)


def load_protocol(path: str | pathlib.Path | None = None) -> Protocol:
    """Load and validate the evaluation protocol. Read-only: never writes
    to `path`. Cached per path, since the lock file does not change during
    a process's lifetime once sealed."""
    resolved = pathlib.Path(path) if path is not None else DEFAULT_LOCK_PATH
    return _load_cached(str(resolved))

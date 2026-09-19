"""Provider protocols and the shared error type (modular-plan.md §2.2).
Every external service is wrapped behind one of these Protocols; callers
never import a concrete `*_local`/`*_google` class directly except
through `factory.get()`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class ProviderError(RuntimeError):
    """Every provider raises this on failure; the API layer maps it to a
    502 (architecture.md §1)."""


@dataclass
class Media:
    data: bytes
    mime: str


@dataclass
class Transcript:
    text: str
    language: str
    confidence: float


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[dict]


class LatLon(Protocol):
    lat: float
    lon: float


class SpeechProvider(Protocol):
    def transcribe(self, audio: bytes, mime: str, lang_hint: str | None = None) -> Transcript: ...


class LLMProvider(Protocol):
    def extract(self, prompt: str, media: list[Media], schema: type) -> tuple[Any, dict[str, float]]: ...
    def generate(self, prompt: str, tools: list[dict] | None = None) -> LLMResponse: ...


class EmbedProvider(Protocol):
    def embed(self, texts: list[str]): ...


class TranslateProvider(Protocol):
    def translate(self, text: str, target_lang: str) -> str: ...


class TTSProvider(Protocol):
    def synthesize(self, text: str, lang: str) -> bytes: ...


class LiveStore(Protocol):
    def put(self, collection: str, doc_id: str, model) -> None: ...
    def get(self, collection: str, doc_id: str): ...
    def query(self, collection: str, filters: dict) -> list: ...
    def watch(self, collection: str, callback: Callable) -> Callable: ...  # returns an unsubscribe fn


class HistoryStore(Protocol):
    def insert(self, table: str, rows: list[dict]) -> None: ...
    def sql(self, query: str, params: tuple | None = None) -> list[dict]: ...


class Queue(Protocol):
    def publish(self, topic: str, payload: dict) -> None: ...
    def subscribe(self, topic: str, handler: Callable) -> None: ...


class Signer(Protocol):
    def sign(self, payload: bytes) -> str: ...
    def verify(self, payload: bytes, signature: str) -> bool: ...


class Messaging(Protocol):
    def send_text(self, to: str, body: str) -> None: ...
    def send_media(self, to: str, url: str) -> None: ...
    def send_buttons(self, to: str, body: str, buttons: list[str]) -> None: ...


class RouteProvider(Protocol):
    def drive_minutes(self, a: LatLon, b: LatLon) -> float: ...

"""Returns the provider implementation for the current mode, memoised
(modular-plan.md §2.2). `AUSHADHI_MODE=local` never constructs a Google
client -- the import of every `*_google` module is deferred to inside the
`cloud` branch, so a local-mode process cannot even attempt to load the
Google SDKs, let alone call them.
"""
from __future__ import annotations

import functools

from backend.config import get_settings

_LOCAL_FACTORIES = {
    "speech": lambda: __import__("backend.providers.speech_local", fromlist=["LocalSpeechProvider"]).LocalSpeechProvider(),
    "llm": lambda: __import__("backend.providers.llm_local", fromlist=["LocalLLMProvider"]).LocalLLMProvider(),
    "embed": lambda: __import__("backend.providers.embed_local", fromlist=["LocalEmbedProvider"]).LocalEmbedProvider(),
    "translate": lambda: __import__("backend.providers.translate_local", fromlist=["LocalTranslateProvider"]).LocalTranslateProvider(),
    "tts": lambda: __import__("backend.providers.tts_local", fromlist=["LocalTTSProvider"]).LocalTTSProvider(),
    "store_live": lambda: __import__("backend.providers.store_live_local", fromlist=["LocalLiveStore"]).LocalLiveStore(),
    "store_history": lambda: __import__("backend.providers.store_history_local", fromlist=["LocalHistoryStore"]).LocalHistoryStore(get_settings().duckdb_path),
    "queue": lambda: __import__("backend.providers.queue_local", fromlist=["LocalQueue"]).LocalQueue(),
    "sign": lambda: __import__("backend.providers.sign_local", fromlist=["LocalSigner"]).LocalSigner(get_settings().signing_key),
    "messaging": lambda: __import__("backend.providers.messaging_local", fromlist=["LocalMessaging"]).LocalMessaging(),
    "routes": lambda: __import__("backend.providers.routes_local", fromlist=["LocalRouteProvider"]).LocalRouteProvider(),
}


def _cloud_factory(name: str):
    # Deferred imports: a local-mode process never even imports the
    # google.* SDKs, let alone constructs a client (architecture.md §2).
    if name == "speech":
        from backend.providers.speech_google import GoogleSpeechProvider
        return GoogleSpeechProvider()
    if name == "llm":
        from backend.providers.llm_google import GoogleLLMProvider
        return GoogleLLMProvider()
    if name == "embed":
        from backend.providers.embed_google import GoogleEmbedProvider
        return GoogleEmbedProvider()
    if name == "translate":
        from backend.providers.translate_google import GoogleTranslateProvider
        return GoogleTranslateProvider()
    if name == "tts":
        from backend.providers.tts_google import GoogleTTSProvider
        return GoogleTTSProvider()
    if name == "store_live":
        from backend.providers.store_live_google import GoogleLiveStore
        return GoogleLiveStore()
    if name == "store_history":
        from backend.providers.store_history_google import GoogleHistoryStore
        return GoogleHistoryStore()
    if name == "queue":
        from backend.providers.queue_google import GooglePubSubQueue
        return GooglePubSubQueue()
    if name == "sign":
        from backend.providers.sign_google import GoogleKMSSigner
        return GoogleKMSSigner()
    if name == "messaging":
        from backend.providers.messaging_google import TwilioMessaging
        return TwilioMessaging()
    if name == "routes":
        from backend.providers.routes_google import GoogleRouteProvider
        return GoogleRouteProvider()
    raise KeyError(f"unknown provider '{name}'")


@functools.lru_cache(maxsize=None)
def get(name: str):
    mode = get_settings().mode
    if mode == "local":
        if name not in _LOCAL_FACTORIES:
            raise KeyError(f"unknown provider '{name}'. Known: {sorted(_LOCAL_FACTORIES)}")
        return _LOCAL_FACTORIES[name]()
    if mode == "cloud":
        return _cloud_factory(name)
    raise ValueError(f"unknown AUSHADHI_MODE '{mode}' (expected 'local' or 'cloud')")

"""Cloud Speech-to-Text v2 (Chirp 2) provider (architecture.md §1's Google
Cloud mapping). Requires GCP credentials and a project -- only constructed
in `AUSHADHI_MODE=cloud` via backend/providers/factory.py's deferred
import, so a local-mode process never even imports `google.cloud.speech_v2`.

Chirp 2 runs only in a few regions, each behind its own endpoint; Singapore is
the nearest to India. Audio format is auto-detected, so WhatsApp voice notes
(OGG/Opus) and browser recordings (WebM/Opus, MP4/AAC) all work unconverted.
"""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import ProviderError, Transcript

CHIRP_LOCATION = "asia-southeast1"


class GoogleSpeechProvider:
    def __init__(self):
        from google.api_core.client_options import ClientOptions
        from google.cloud import speech_v2

        self._types = speech_v2.types
        self._client = speech_v2.SpeechClient(client_options=ClientOptions(api_endpoint=f"{CHIRP_LOCATION}-speech.googleapis.com"))
        self._recognizer = f"projects/{get_settings().gcp_project}/locations/{CHIRP_LOCATION}/recognizers/_"

    def transcribe(self, audio: bytes, mime: str, lang_hint: str | None = None) -> Transcript:
        # Language is detected, not taken from `lang_hint`: nurses mix languages, and with an
        # English hint a Hindi note "ओआरएस 50 जिंक 120" came back as "50 zinc 120".
        config = self._types.RecognitionConfig(
            auto_decoding_config=self._types.AutoDetectDecodingConfig(),
            language_codes=["auto"],
            model="chirp_2",
        )
        try:
            response = self._client.recognize(request=self._types.RecognizeRequest(recognizer=self._recognizer, config=config, content=audio))
        except Exception as e:  # noqa: BLE001 -- any Google API error becomes a ProviderError
            raise ProviderError(f"Chirp transcription failed: {e}") from e

        if not response.results or not response.results[0].alternatives:
            raise ProviderError("Chirp returned no transcription result")
        best = response.results[0].alternatives[0]
        return Transcript(
            text=best.transcript, language=response.results[0].language_code or "unknown",
            confidence=float(getattr(best, "confidence", 0.0)),
        )

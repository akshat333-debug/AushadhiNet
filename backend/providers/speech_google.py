"""Cloud Speech-to-Text v2 (Chirp 2) provider (architecture.md §1's Google
Cloud mapping). Requires GCP credentials and a project -- only constructed
in `AUSHADHI_MODE=cloud` via backend/providers/factory.py's deferred
import, so a local-mode process never even imports `google.cloud.speech`.
"""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import ProviderError, Transcript


class GoogleSpeechProvider:
    def __init__(self):
        from google.cloud import speech

        self._client = speech.SpeechClient()
        self._speech = speech
        self._project = get_settings().gcp_project

    def transcribe(self, audio: bytes, mime: str, lang_hint: str | None = None) -> Transcript:
        encoding_map = {
            "audio/ogg": self._speech.ExplicitDecodingConfig.AudioEncoding.OGG_OPUS,
            "audio/amr": self._speech.ExplicitDecodingConfig.AudioEncoding.AMR,
            "audio/mpeg": self._speech.ExplicitDecodingConfig.AudioEncoding.MP3,
        }
        config = self._speech.RecognitionConfig(
            explicit_decoding_config=self._speech.ExplicitDecodingConfig(
                encoding=encoding_map.get(mime, self._speech.ExplicitDecodingConfig.AudioEncoding.OGG_OPUS),
                sample_rate_hertz=16000, audio_channel_count=1,
            ),
            language_codes=[lang_hint] if lang_hint else ["mr-IN", "hi-IN", "en-IN"],
            model="chirp_2",
        )
        request = self._speech.RecognizeRequest(
            recognizer=f"projects/{self._project}/locations/global/recognizers/_",
            config=config, content=audio,
        )
        try:
            response = self._client.recognize(request=request)
        except Exception as e:  # noqa: BLE001 -- any Google API error becomes a ProviderError
            raise ProviderError(f"Chirp transcription failed: {e}") from e

        if not response.results or not response.results[0].alternatives:
            raise ProviderError("Chirp returned no transcription result")
        best = response.results[0].alternatives[0]
        return Transcript(
            text=best.transcript, language=response.results[0].language_code or "unknown",
            confidence=float(getattr(best, "confidence", 0.0)),
        )

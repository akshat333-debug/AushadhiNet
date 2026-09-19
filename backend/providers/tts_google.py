"""Cloud Text-to-Speech provider (architecture.md §1), used for local-
language voice alerts."""
from __future__ import annotations

from backend.providers.base import ProviderError

_VOICE_BY_LANG = {"mr": "mr-IN-Standard-A", "hi": "hi-IN-Standard-A", "en": "en-IN-Standard-A"}


class GoogleTTSProvider:
    def __init__(self):
        from google.cloud import texttospeech

        self._client = texttospeech.TextToSpeechClient()
        self._tts = texttospeech

    def synthesize(self, text: str, lang: str) -> bytes:
        tts = self._tts
        voice_name = _VOICE_BY_LANG.get(lang, _VOICE_BY_LANG["en"])
        try:
            response = self._client.synthesize_speech(
                input=tts.SynthesisInput(text=text),
                voice=tts.VoiceSelectionParams(language_code=voice_name.rsplit("-", 1)[0], name=voice_name),
                audio_config=tts.AudioConfig(audio_encoding=tts.AudioEncoding.OGG_OPUS),
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"TTS synthesis failed: {e}") from e
        return response.audio_content

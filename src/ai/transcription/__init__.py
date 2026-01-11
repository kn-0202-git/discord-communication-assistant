"""音声文字起こしプロバイダーモジュール

このモジュールは、音声ファイルを文字起こしするためのプロバイダーを提供します。

Example:
    >>> from src.ai.transcription import WhisperProvider
    >>> provider = WhisperProvider(api_key="sk-...", model="whisper-1")
    >>> text = await provider.transcribe(audio_bytes)
"""

from src.ai.transcription.base import TranscriptionProvider
from src.ai.transcription.whisper import WhisperProvider

__all__ = ["TranscriptionProvider", "WhisperProvider"]

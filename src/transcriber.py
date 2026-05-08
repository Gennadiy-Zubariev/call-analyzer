from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class Transcriber(ABC):
    """Базовий клас для транскрибаторів. Реалізації: LocalWhisperTranscriber, OpenAIWhisperTranscriber."""

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str = "uk") -> str:
        """Транскрибує аудіофайл і повертає текст."""


class LocalWhisperTranscriber(Transcriber):
    """faster-whisper локально. Модель завантажиться при першому виклику."""

    def __init__(self, model_size: str = "large-v3", device: str = "auto") -> None:
        from faster_whisper import WhisperModel

        compute_type = "float16" if device == "cuda" else "int8"
        logger.info("Завантажую модель %s (device=%s, compute=%s)", model_size, device, compute_type)
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: Path, language: str = "uk") -> str:
        logger.info("Транскрибую %s ...", audio_path.name)
        segments, info = self.model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=True,  # відсікає тишу — швидше і чистіше
            beam_size=5,
        )
        parts = [seg.text.strip() for seg in segments]
        text = " ".join(parts).strip()
        logger.info(
            "Готово: %d символів, тривалість аудіо ~%.1f с",
            len(text), info.duration
        )
        return text


class OpenAIWhisperTranscriber(Transcriber):
    """Whisper через OpenAI API. Потрібен ключ і інтернет."""

    def __init__(self, api_key: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    def transcribe(self, audio_path: Path, language: str = "uk") -> str:
        logger.info("Транскрибую через OpenAI API: %s", audio_path.name)
        with audio_path.open("rb") as f:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language,
            )
        return response.text


def make_transcriber(backend: str, **kwargs) -> Transcriber:
    """Фабрика. backend: 'whisper_local' | 'openai_api'."""
    if backend == "whisper_local":
        return LocalWhisperTranscriber(
            model_size=kwargs.get("whisper_model", "large-v3"),
            device=kwargs.get("whisper_device", "auto"),
        )
    if backend == "openai_api":
        return OpenAIWhisperTranscriber(api_key=kwargs["openai_api_key"])
    raise ValueError(f"Невідомий backend: {backend}")

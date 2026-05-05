"""Транскрибація аудіо. Підтримує локальний faster-whisper і OpenAI API."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class Transcriber(ABC):
    """Абстрактний базовий клас. Усі реалізації мають повертати рядок-транскрипт."""

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str = "uk") -> str:
        ...


class LocalWhisperTranscriber(Transcriber):
    """faster-whisper локально. Модель завантажується при першому виклику."""

    def __init__(self, model_size: str = "large-v3", device: str = "auto") -> None:
        # TODO:
        # 1. from faster_whisper import WhisperModel
        # 2. визначити compute_type залежно від device ("float16" для cuda, "int8" інакше)
        # 3. self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        raise NotImplementedError

    def transcribe(self, audio_path: Path, language: str = "uk") -> str:
        # TODO:
        # 1. self.model.transcribe(str(audio_path), language=..., vad_filter=True, beam_size=5)
        # 2. зібрати text з усіх segment.text
        # 3. повернути " ".join(parts).strip()
        raise NotImplementedError


class OpenAIWhisperTranscriber(Transcriber):
    """Whisper через OpenAI API."""

    def __init__(self, api_key: str) -> None:
        # TODO: from openai import OpenAI; self.client = OpenAI(api_key=api_key)
        raise NotImplementedError

    def transcribe(self, audio_path: Path, language: str = "uk") -> str:
        # TODO:
        # 1. open audio_path в "rb"
        # 2. self.client.audio.transcriptions.create(model="whisper-1", file=f, language=language)
        # 3. повернути response.text
        raise NotImplementedError


def make_transcriber(backend: str, **kwargs) -> Transcriber:
    """Фабрика. backend: 'whisper_local' | 'openai_api'."""
    # TODO:
    # if backend == "whisper_local": повернути LocalWhisperTranscriber(...)
    # elif backend == "openai_api": повернути OpenAIWhisperTranscriber(...)
    # else: raise ValueError
    raise NotImplementedError

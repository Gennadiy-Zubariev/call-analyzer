from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from config import DOWNLOADS_DIR, Settings
from src.analyzer import OllamaAnalyzer
from src.drive_client import DriveClient
from src.sheets_client import SheetsClient
from src.transcriber import Transcriber, make_transcriber

logger = logging.getLogger(__name__)


# 2025-09-10_15-52_0632838007_incoming.mp3
FILENAME_DATE_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})[_-](\d{2})[-:](\d{2})")


class CallProcessingPipeline:
    """Оркеструє повний цикл обробки: скачування аудіо → транскрипція → аналіз → запис у таблицю."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.drive = DriveClient(settings.google_service_account_file)
        self.sheets = SheetsClient(self.drive.credentials)
        self.transcriber: Transcriber | None = None  # лінива ініціалізація
        self.analyzer = OllamaAnalyzer(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )

    def _ensure_transcriber(self) -> Transcriber:
        if self.transcriber is None:
            self.transcriber = make_transcriber(
                self.settings.transcription_backend,
                whisper_model=self.settings.whisper_model,
                whisper_device=self.settings.whisper_device,
                openai_api_key=self.settings.openai_api_key,
            )
        return self.transcriber

    def _ensure_work_sheet(self) -> str:
        sheet_id = self.settings.work_sheet_id
        logger.info("Використовую існуючу таблицю: %s", sheet_id)
        self.sheets.ensure_headers(sheet_id)
        return sheet_id

    def run(self) -> None:
        """Запускає повний пайплайн для всіх аудіофайлів із source-папки."""
        self.settings.validate_required()

        logger.info("=" * 60)
        logger.info("Старт пайплайну обробки дзвінків СТО")
        logger.info("=" * 60)

        # 1. Знайти аудіо в source-папці
        audio_files = self.drive.list_audio_files(self.settings.source_drive_folder_id)
        if not audio_files:
            logger.warning("У source-папці немає аудіо. Виходжу.")
            return

        # 2. Підготувати робочу таблицю
        work_sheet_id = self._ensure_work_sheet()

        # 3. По кожному файлу — повний цикл
        success_count = 0
        for f in tqdm(audio_files, desc="Аудіофайли", unit="файл"):
            try:
                self._process_one(f, work_sheet_id)
                success_count += 1
            except Exception as e:
                logger.exception("Помилка на файлі %s: %s", f.get("name"), e)

        logger.info(
            "Готово. Опрацьовано %d/%d. Таблиця: https://docs.google.com/spreadsheets/d/%s",
            success_count, len(audio_files), work_sheet_id
        )

    def _process_one(self, file_meta: dict, work_sheet_id: str) -> None:
        """Повний цикл обробки одного файлу."""
        name = file_meta["name"]
        file_id = file_meta["id"]
        logger.info("\n--- %s ---", name)

        # 1. Завантажуємо аудіо локально (якщо ще немає)
        local_audio = DOWNLOADS_DIR / name
        if not local_audio.exists():
            self.drive.download_file(file_id, local_audio)
        else:
            logger.info("Аудіо вже скачане локально, пропускаю")

        # 2. Транскрибуємо (якщо ще немає .txt)
        local_transcript = local_audio.with_suffix(".txt")
        if local_transcript.exists():
            logger.info("Транскрипт уже є локально, читаю з кешу")
            transcript_text = local_transcript.read_text(encoding="utf-8")
        else:
            transcriber = self._ensure_transcriber()
            transcript_text = transcriber.transcribe(local_audio, language="uk")
            local_transcript.write_text(transcript_text, encoding="utf-8")
            logger.info("Транскрипт збережено: %s", local_transcript)

        # 3. LLM-аналіз
        analysis = self.analyzer.analyze(transcript_text)

        # 4. Витягаємо дату дзвінка
        date = self._extract_call_date(name, file_meta)

        # 5. Записуємо рядок у таблицю
        # Передаємо тільки початок транскрипту (Sheets ліміт ~50000 знаків на комірку,
        # але довгі тексти роблять таблицю некрасивою)
        transcript_preview = (
            transcript_text[:500] + "..." if len(transcript_text) > 500 else transcript_text
        )
        self.sheets.append_call_row(
            sheet_id=work_sheet_id,
            date=date,
            analysis=analysis,
            transcript=transcript_preview,
        )

    @staticmethod
    def _extract_call_date(filename: str, file_meta: dict) -> datetime:
        """Витягує дату з імені файлу (типовий формат телефонії), інакше — createdTime."""
        m = FILENAME_DATE_PATTERN.search(filename)
        if m:
            try:
                year, month, day, hour, minute = map(int, m.groups())
                return datetime(year, month, day, hour, minute)
            except ValueError:
                pass

        created = file_meta.get("createdTime", "")
        try:
            return datetime.fromisoformat(created.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.now()

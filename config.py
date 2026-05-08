from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.resolve()
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)


class Settings(BaseModel):
    # Google
    google_service_account_file: Path
    source_drive_folder_id: str
    work_drive_folder_id: str
    work_sheet_id: str = ""

    # Транскрибація
    transcription_backend: Literal["whisper_local", "openai_api"] = "whisper_local"
    whisper_model: str = "large-v3"
    whisper_device: Literal["cpu", "cuda", "auto"] = "auto"
    openai_api_key: str = ""

    # LLM (локальний Ollama)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Інше
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            google_service_account_file=Path(
                os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service-account.json")
            ),
            source_drive_folder_id=os.getenv("SOURCE_DRIVE_FOLDER_ID", ""),
            work_drive_folder_id=os.getenv("WORK_DRIVE_FOLDER_ID", ""),
            work_sheet_id=os.getenv("WORK_SHEET_ID", ""),
            transcription_backend=os.getenv("TRANSCRIPTION_BACKEND", "whisper_local"),
            whisper_model=os.getenv("WHISPER_MODEL", "large-v3"),
            whisper_device=os.getenv("WHISPER_DEVICE", "auto"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def validate_required(self) -> None:
        """Перевірка обов'язкових полів перед запуском пайплайну."""
        missing = []
        if not self.google_service_account_file.exists():
            missing.append(f"Файл {self.google_service_account_file} не знайдено")
        if not self.source_drive_folder_id:
            missing.append("SOURCE_DRIVE_FOLDER_ID")
        if self.transcription_backend == "openai_api" and not self.openai_api_key:
            missing.append("OPENAI_API_KEY (бо вибраний backend openai_api)")

        if missing:
            raise ValueError("Не вистачає налаштувань:\n- " + "\n- ".join(missing))


settings = Settings.from_env()


# ===========================================================================
# Перелік "Топ робіт".
# LLM обирає рівно одне значення зі списку. Якщо нічого не підходить — OTHER.
# ===========================================================================
WORK_TYPES = [
    "Комп'ютерна діагностика",
    "Заміна оливи ДВЗ + масляний фільтр",
    "Комплексна діагностика",
    "Ендоскопія",
    "Заміна повітряного фільтра ДВЗ",
    "Заміна фільтра салону в салонному відділенні",
    "Заміна сайлентблоку",
    "Зняття / встановлення важіля",
    "Заміна еластичної муфти карданного валу",
    "Слюсарні роботи",
    "Зняття / встановлення важіля прд.",
    "Заміна амортизатора переднього",
    "Заміна оливи АКПП",
    "Мийка / чистка деталі",
    "Зняття / встановлення повітряного патрубка",
    "Заміна охолоджувальної рідини",
    "Заміна гальмівної рідини з прокачкою",
    "Заміна оливи в зд. редукторі",
    "Кодування опцій",
    "Заміна амортизатора зд.",
    "Заміна гальмівних дисків та колодок прд.",
    "Комплексне ТО",
]
OTHER_WORK_TYPE = "інший варіант"
ALL_WORK_TYPES = [*WORK_TYPES, OTHER_WORK_TYPE]


# ===========================================================================
# Колонки фінальної таблиці.
#
# Двохрядковий заголовок: row 1 — групи, row 2 — реальні поля.
# ===========================================================================

# Group → колонки в цій групі (для row 1, з мерджем).
HEADER_GROUPS: list[tuple[str, int]] = [
    ("Ідентифікація", 6),       # A-E
    ("Скрипт", 1),              # F
    ("Інформація про автомобіль", 3),  # G-I
    ("ДОП продажі", 2),         # J-K
    ("Скрипт", 2),              # L-M
    ("Інфо", 3),                # N-P
    ("Результат", 4),           # Q-T
    ("", 1),                    # U — Сума балів (своя колонка без групи)
]

SHEET_HEADERS = [
    # Ідентифікація
    "Дата",
    "Транскрибація",
    "Тип звернення",
    "Номер телефону",
    "Філія",
    "Менеджер",
    # Скрипт
    "Початок розмови, представлення",
    # Інформація про автомобіль
    "Чи дізнвся менеджер кузов атвомобіля",
    "Чи дізнався менеджер рік автомобіля",
    "Чи дізнався менеджр пробіг",
    # ДОП продажі
    "Пропозиція про комплексну діагностику",
    "Дізнався які роботи робилися раніше",
    # Скрипт (продовження)
    "Запис на сервіс, Дата",
    "Завершення розмови прощання",
    # Інфо
    "Яка робота з топ 100",
    "Чи дотримувався всіх інструкцій з топ 100 робіт Так/Ні",
    "Яких рекоменадцій менеджер не дотримувався з топ 100 робіт",
    # Результат
    "Результат",
    "Оцінка",
    "Запчастини",
    "Коментар",
    # Підрахунок (наша додаткова колонка)
    "Сума балів",
]

# Колонки з бінарними оцінками (індекси в SHEET_HEADERS, 0-based)
# F=5, G=6, H=7, I=8, J=9, K=10, M=12, O=14
BINARY_COLUMN_INDEXES = [5, 6, 7, 8, 9, 10, 12, 14]

# Допустимі значення для деяких полів (для валідації LLM-виходу)
CALL_TYPES = ["Авто в роботі", "Консультація", "Вхідний дзвінок", "Пропущений", "Інше"]
RESULTS = ["Запис", "Запис на сервіс", "Передзвонити", "Повторно консультація", "Інше"]
PARTS_OPTIONS = ["Наші", "Клієнта", ""]

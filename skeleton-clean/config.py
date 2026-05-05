"""Централізована конфігурація. Читає .env, валідує, дає типізований доступ."""
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
    """Усі налаштування з .env у типізованому вигляді."""
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
        """Створює Settings з .env."""
        # TODO: повернути cls(...) із os.getenv() для кожного поля
        raise NotImplementedError

    def validate_required(self) -> None:
        """Перевіряє обовʼязкові поля. Кидає ValueError якщо чогось бракує."""
        # TODO: зібрати список missing і кинути ValueError якщо непорожній
        raise NotImplementedError


# Створюємо одну глобальну instance — імпортуємо її з інших модулів
# settings = Settings.from_env()  # розкоментувати після реалізації from_env


# ===========================================================================
# Бізнес-константи: перелік "Топ робіт" зі скрина шаблонної таблиці.
# ===========================================================================
WORK_TYPES: list[str] = [
    # TODO: вставити 22 пункти зі скрина
]
OTHER_WORK_TYPE = "інший варіант"
ALL_WORK_TYPES = [*WORK_TYPES, OTHER_WORK_TYPE]


# ===========================================================================
# Структура заголовків таблиці-звіту.
# Group → скільки колонок займає у row 1 (для merge cells).
# ===========================================================================
HEADER_GROUPS: list[tuple[str, int]] = [
    # TODO: вставити список (назва_групи, кількість_колонок)
]

SHEET_HEADERS: list[str] = [
    # TODO: 21 колонка точно по шаблону
]

# Індекси бінарних колонок (0-based) у SHEET_HEADERS
BINARY_COLUMN_INDEXES: list[int] = [
    # TODO: вписати індекси F, G, H, I, J, K, M, O
]

# Допустимі значення для деяких полів
CALL_TYPES = ["Авто в роботі", "Консультація", "Вхідний дзвінок", "пропущений", "Інше"]
RESULTS = ["Запис", "Запис на сервіс", "Передзвонити", "Повторно консультація", "Інше"]
PARTS_OPTIONS = ["Наші", "Клієнта", ""]

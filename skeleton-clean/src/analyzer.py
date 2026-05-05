"""LLM-аналіз транскрипту дзвінка СТО через локальний Ollama."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from config import ALL_WORK_TYPES, CALL_TYPES, OTHER_WORK_TYPE, PARTS_OPTIONS, RESULTS

logger = logging.getLogger(__name__)


class CallAnalysis(BaseModel):
    """Структурований результат аналізу одного дзвінка.
    
    Точна відповідність колонкам шаблонної таблиці.
    """
    # Ідентифікація
    call_type: str = Field(description="Тип звернення")
    phone: str = Field(default="", description="Номер телефону")
    branch: str = Field(default="", description="Філія")
    manager: str = Field(default="", description="Імʼя менеджера")

    # 8 бінарних оцінок
    greeting: int = Field(ge=0, le=1, description="Привітався і представився")
    asked_body: int = Field(ge=0, le=1, description="Дізнався кузов авто")
    asked_year: int = Field(ge=0, le=1, description="Дізнався рік")
    asked_mileage: int = Field(ge=0, le=1, description="Дізнався пробіг")
    offered_complex_diag: int = Field(ge=0, le=1, description="Запропонував комплексну діагностику")
    asked_previous_works: int = Field(ge=0, le=1, description="Дізнався які роботи робилися раніше")
    farewell: int = Field(ge=0, le=1, description="Завершив розмову, попрощався")
    followed_top100_instructions: int = Field(ge=0, le=1, description="Дотримувався інструкцій")

    # Текстові поля
    appointment_date: str = Field(default="", description="Дата запису на сервіс")
    work_type: str = Field(description="Робота з переліку Топ-100")
    missed_recommendations: str = Field(default="", description="Які рекомендації пропустив")
    result: str = Field(description="Результат")
    parts: str = Field(default="", description="Запчастини")
    score: int = Field(ge=0, le=10, description="Загальна оцінка 1-10")
    comment: str = Field(description="Коментар")
    is_problematic: bool = Field(description="Чи проблемний дзвінок")

    @property
    def total_score(self) -> int:
        """Сума 8 бінарних критеріїв."""
        # TODO: повернути суму всіх бінарних полів
        raise NotImplementedError


# Промпти — вписуємо повністю, бо це не код а дані
SYSTEM_PROMPT = """Ти — досвідчений аудитор якості клієнтських дзвінків автосервісу (СТО). \
Аналізуй транскрипти розмов українською мовою.

Відповідай ТІЛЬКИ валідним JSON-обʼєктом без markdown-обгорток і додаткових слів."""


USER_TEMPLATE = """ПЕРЕЛІК ДОПУСТИМИХ ТИПІВ РОБІТ:
{work_types}

КРИТЕРІЇ ОЦІНКИ (кожен 0 або 1):
1. greeting — привітався, представився
2. asked_body — дізнався кузов авто
3. asked_year — дізнався рік випуску
4. asked_mileage — дізнався пробіг
5. offered_complex_diag — запропонував комплексну діагностику
6. asked_previous_works — спитав які роботи робилися раніше
7. farewell — попрощався
8. followed_top100_instructions — дотримувався скрипта

is_problematic = true коли менеджер грубий, мат, некоректна інформація, конфлікт.

ТИП ЗВЕРНЕННЯ: один з {call_types}
РЕЗУЛЬТАТ: один з {results}
ЗАПЧАСТИНИ: одне з {parts_options}

ТРАНСКРИПТ:
\"\"\"
{transcript}
\"\"\"

Поверни JSON суворо такої структури:
{{
  "call_type": "...",
  "phone": "...",
  "branch": "...",
  "manager": "...",
  "greeting": 0,
  "asked_body": 0,
  "asked_year": 0,
  "asked_mileage": 0,
  "offered_complex_diag": 0,
  "asked_previous_works": 0,
  "farewell": 0,
  "followed_top100_instructions": 0,
  "appointment_date": "",
  "work_type": "<точна назва зі списку>",
  "missed_recommendations": "",
  "result": "...",
  "parts": "",
  "score": 0,
  "comment": "...",
  "is_problematic": false
}}"""


class OllamaAnalyzer:
    """Аналіз через локальний Ollama. JSON mode + ретраї + нормалізація."""

    def __init__(self, host: str, model: str, max_retries: int = 3) -> None:
        # TODO:
        # 1. from ollama import Client; self.client = Client(host=host)
        # 2. self.model = model; self.max_retries = max_retries
        # 3. self._check_model_available()
        raise NotImplementedError

    def _check_model_available(self) -> None:
        """Перевіряє чи модель завантажена. Якщо ні — попереджає у логах."""
        # TODO:
        # 1. self.client.list() -> {"models": [...]}
        # 2. перевірити чи self.model.split(":")[0] є в списку
        # 3. якщо ні — logger.warning з підказкою "ollama pull ..."
        raise NotImplementedError

    def analyze(self, transcript: str) -> CallAnalysis:
        """Головний метод. Викликає LLM, парсить, нормалізує, повертає CallAnalysis."""
        # TODO:
        # 1. якщо транскрипт порожній — повернути self._fallback(...)
        # 2. сформувати user_msg через USER_TEMPLATE.format(...)
        # 3. цикл ретраїв max_retries раз:
        #    - raw = self._call_ollama(user_msg)
        #    - data = self._extract_json(raw)
        #    - analysis = CallAnalysis(**data)
        #    - analysis.work_type = self._normalize_work_type(analysis.work_type)
        #    - return analysis
        #    у except (JSONDecodeError, ValidationError, ValueError) — sleep і повтор
        # 4. якщо всі спроби невдалі — self._fallback(...)
        raise NotImplementedError

    def _call_ollama(self, user_msg: str) -> str:
        """Викликає Ollama в JSON mode. Повертає сирий рядок-відповідь."""
        # TODO:
        # 1. self.client.chat(model=..., messages=[system, user], format="json", options={...})
        # 2. повернути response["message"]["content"].strip()
        raise NotImplementedError

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        """Дістає JSON з відповіді. Видаляє markdown-огорточку якщо є."""
        # TODO:
        # 1. strip()
        # 2. якщо починається з ``` — обрізати огортку
        # 3. якщо є зайвий текст — взяти підрядок від першої { до останньої }
        # 4. json.loads(text)
        raise NotImplementedError

    @staticmethod
    def _normalize_work_type(raw: str) -> str:
        """Приводить назву роботи до точного значення зі списку ALL_WORK_TYPES."""
        # TODO:
        # 1. якщо порожньо -> OTHER_WORK_TYPE
        # 2. точне співпадіння (case-insensitive)
        # 3. часткове співпадіння — найбільший збіг ключових слів (>=4 символи)
        # 4. якщо нічого -> OTHER_WORK_TYPE
        raise NotImplementedError

    @staticmethod
    def _fallback(reason: str) -> CallAnalysis:
        """Фолбек коли LLM не зміг — повертає мінімально валідний обʼєкт."""
        # TODO: повернути CallAnalysis з усіма нулями, is_problematic=True,
        # comment починається з "[АВТО-ФОЛБЕК]"
        raise NotImplementedError

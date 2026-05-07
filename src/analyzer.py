from __future__ import annotations

import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from config import ALL_WORK_TYPES, CALL_TYPES, OTHER_WORK_TYPE, PARTS_OPTIONS, RESULTS

logger = logging.getLogger(__name__)


class CallAnalysis(BaseModel):
    """Структурований результат аналізу одного дзвінка."""

    # Ідентифікація
    call_type: str = Field(description="Тип звернення: Авто в роботі / Консультація / Вхідний дзвінок / Пропущений / Інше")
    phone: str = Field(default="", description="Номер телефону клієнта якщо згадано")
    branch: str = Field(default="", description="Філія: Київ / ОДС / ЛВВ / ЗПР тощо")
    manager: str = Field(default="", description="Імʼя менеджера якщо представився")

    # Скрипт + Інформація про авто (8 бінарних)
    greeting: int = Field(ge=0, le=1, description="Привітався і представився")
    asked_body: int = Field(ge=0, le=1, description="Дізнався кузов авто")
    asked_year: int = Field(ge=0, le=1, description="Дізнався рік авто")
    asked_mileage: int = Field(ge=0, le=1, description="Дізнався пробіг")
    offered_complex_diag: int = Field(ge=0, le=1, description="Запропонував комплексну діагностику")
    asked_previous_works: int = Field(ge=0, le=1, description="Дізнався які роботи робилися раніше")
    farewell: int = Field(ge=0, le=1, description="Завершив розмову, попрощався")
    followed_top100_instructions: int = Field(ge=0, le=1, description="Дотримувався інструкцій з топ-100")

    # Текстові поля
    appointment_date: str = Field(default="", description="Дата запису на сервіс якщо є")
    work_type: str = Field(description="Робота з переліку 'Топ-100'")
    missed_recommendations: str = Field(default="", description="Яких рекомендацій не дотримувався")
    result: str = Field(description="Результат: Запис / Передзвонити / Повторно консультація / Інше")
    parts: str = Field(default="", description="Запчастини: Наші / Клієнта / порожньо")
    score: int = Field(ge=0, le=10, description="Загальна оцінка менеджера 1-10")
    comment: str = Field(description="Коментар, особливо якщо є проблеми")
    is_problematic: bool = Field(description="True якщо менеджер працював погано/некоректно")

    @property
    def total_score(self) -> int:
        """Сума 8 бінарних критеріїв."""
        return (
            self.greeting + self.asked_body + self.asked_year + self.asked_mileage
            + self.offered_complex_diag + self.asked_previous_works
            + self.farewell + self.followed_top100_instructions
        )


SYSTEM_PROMPT = """Ти — досвідчений аудитор якості клієнтських дзвінків автосервісу (СТО). \
Ти аналізуєш транскрипти розмов менеджера СТО з клієнтами українською мовою.

Твоє завдання — заповнити структуровану картку дзвінка для звіту керівнику. \
Відповідай ТІЛЬКИ валідним JSON-обʼєктом без жодних додаткових слів, коментарів \
чи markdown-обгорток. Тільки JSON."""


USER_TEMPLATE = """КОНТЕКСТ:
Це транскрипт дзвінка в автосервіс СТО. МЕНЕДЖЕР автосервісу приймає вхідні дзвінки від КЛІЄНТІВ.
- МЕНЕДЖЕР — той, хто ВІДПОВІДАЄ на дзвінок. На початку зазвичай представляється: "Доброго дня, [ім'я]", "Слухаю вас", "[компанія], [ім'я]".
- КЛІЄНТ — той, хто ТЕЛЕФОНУЄ. Каже: "хочу записатись", "у мене проблема...", "хочу на ТО".

Якщо обидва представляються — МЕНЕДЖЕР це той, хто говорить ПЕРШИМ і відповідає на дзвінок.

ПЕРЕЛІК ДОПУСТИМИХ ТИПІВ РОБІТ:
{work_types}
ОЦІНЮВАНІ КРИТЕРІЇ (кожен 0 або 1):
КРИТЕРІЇ ОЦІНКИ (кожен 0 або 1, оцінюємо роботу МЕНЕДЖЕРА):
1. greeting — менеджер привітався і представився (назвав ім'я або компанію). 1 якщо у тексті є привітання + представлення менеджера.
2. asked_body — менеджер дізнався модель/марку автомобіля клієнта (наприклад: BMW 540, Toyota Camry, Audi A6). 1 якщо в тексті згадана конкретна модель авто, незалежно чи прямо питав менеджер чи клієнт сам сказав. 0 якщо марка авто взагалі не згадана.
3. asked_year — менеджер дізнався рік випуску автомобіля. 1 якщо у тексті згаданий рік авто (наприклад: "2018 року", "16-го року"). 0 якщо рік взагалі не обговорювався.
4. asked_mileage — менеджер дізнався пробіг автомобіля. 1 якщо у тексті згадані конкретні цифри пробігу (наприклад: "150 тисяч", "200к км"). 0 якщо пробіг не обговорювався.
5. offered_complex_diag — менеджер запропонував комплексну діагностику. 1 якщо менеджер активно пропонує діагностику (а не просто погоджується на запит клієнта).
6. asked_previous_works — менеджер дізнався які роботи робилися раніше з цим авто. 1 якщо у розмові обговорювались попередні ремонти/ТО (незалежно прямо питав менеджер чи клієнт сам розповів).
7. farewell — менеджер попрощався (подякував / "до побачення" / "гарного дня" / "дякую").
8. followed_top100_instructions — менеджер пройшов основні етапи скрипту: привітався, з'ясував потребу, дізнався про авто, запропонував рішення, записав. 1 якщо більшість етапів виконана.

is_problematic = TRUE тільки у наступних випадках:
- менеджер вживає мат, нецензурну лексику
- менеджер грубий або зневажливий до клієнта
- менеджер дав явно НЕВІРНУ або шкідливу інформацію
- виник КОНФЛІКТ або агресія
- менеджер відмовив без обґрунтування і альтернативи
- клієнт залишився БЕЗ ВИРІШЕННЯ і незадоволеним

is_problematic = FALSE у всіх інших випадках, ВКЛЮЧНО з:
- менеджер не задав усі ідеальні питання (це нормально)
- розмова коротка або по-діловому (це нормально)
- клієнт сам ухилився від відповіді (це не вина менеджера)
- менеджер забув один з пунктів скрипту (це не "проблема", просто нижча сума балів)
- транскрипт містить помилки розпізнавання

ПРИКЛАД:
- Менеджер привітався, спитав про авто, записав на ТО, попрощався → is_problematic=FALSE (звичайна робота)
- Менеджер каже клієнту "ну ви що, не можете зрозуміти?" → is_problematic=TRUE (грубість)
- Менеджер не запитав про пробіг → is_problematic=FALSE (просто greeting=1, asked_mileage=0, не "проблема")

ТИП ЗВЕРНЕННЯ: один з {call_types}
РЕЗУЛЬТАТ: один з {results}
ЗАПЧАСТИНИ: одне з {parts_options}. ВАЖЛИВО: повертайте порожній рядок "" якщо тема запчастин або деталей у розмові не обговорювалась. НЕ ВГАДУЙТЕ.

ТРАНСКРИПТ:
\"\"\"
{transcript}
\"\"\"

Поверни JSON суворо такої структури (без зайвих полів):
{{
  "call_type": "...",
  "phone": "<номер або порожньо>",
  "branch": "<філія або порожньо>",
  "manager": "<імʼя того хто ПРИЙМАЄ дзвінок, не клієнта>",
  "greeting": 0,
  "asked_body": 0,
  "asked_year": 0,
  "asked_mileage": 0,
  "offered_complex_diag": 0,
  "asked_previous_works": 0,
  "farewell": 0,
  "followed_top100_instructions": 0,
  "appointment_date": "<дата запису якщо є, або порожньо>",
  "work_type": "<точна назва зі списку 'Топ-100', або 'інший варіант'>",
  "missed_recommendations": "<які рекомендації менеджер пропустив>",
  "result": "...",
  "parts": "<Наші | Клієнта | порожньо>",
  "score": <число 1-10>,
  "comment": "<стислий коментар, особливо про проблеми>",
  "is_problematic": false
}}"""


class OllamaAnalyzer:
    """Аналіз через локальний Ollama. JSON mode + ретраї + нормалізація типу робіт."""

    def __init__(self, host: str, model: str, max_retries: int = 3) -> None:
        from ollama import Client

        self.client = Client(host=host)
        self.model = model
        self.max_retries = max_retries
        self._check_model_available()

    def _check_model_available(self) -> None:
        try:
            response = self.client.list()
            available = [m.get("name") or m.get("model") for m in response.get("models", [])]
            base = self.model.split(":")[0]
            if not any(name and name.startswith(base) for name in available):
                logger.warning(
                    "Модель %s не знайдено локально. Виконайте: ollama pull %s",
                    self.model, self.model
                )
        except Exception as e:
            logger.warning("Не вдалося перевірити доступні моделі: %s", e)

    def analyze(self, transcript: str) -> CallAnalysis:
        if not transcript.strip():
            return self._fallback("Транскрипт порожній")

        user_msg = USER_TEMPLATE.format(
            work_types="\n".join(f"- {wt}" for wt in ALL_WORK_TYPES),
            call_types=" / ".join(CALL_TYPES),
            results=" / ".join(RESULTS),
            parts_options=" / ".join(repr(p) for p in PARTS_OPTIONS),
            transcript=transcript,
        )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw = self._call_ollama(user_msg)
                data = self._extract_json(raw)
                analysis = CallAnalysis(**data)
                # Нормалізуємо work_type — щоб не було відсебеньки
                analysis.work_type = self._normalize_work_type(analysis.work_type)
                return analysis
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                last_error = e
                logger.warning("Спроба %d/%d не вдалась: %s", attempt, self.max_retries, e)
                if attempt < self.max_retries:
                    time.sleep(1)
            except Exception as e:
                last_error = e
                logger.error("Помилка виклику Ollama: %s", e)
                break

        return self._fallback(f"LLM не зміг проаналізувати: {last_error}")

    def _call_ollama(self, user_msg: str) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            format="json",
            options={
                "temperature": 0.2,
                "num_ctx": 8192,
            },
        )
        return response["message"]["content"].strip()

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                text = text[start:end + 1]
        return json.loads(text)

    @staticmethod
    def _normalize_work_type(raw: str) -> str:
        """LLM любить вигадувати — приводимо до точної назви зі списку."""
        if not raw:
            return OTHER_WORK_TYPE
        raw_lower = raw.strip().lower()
        # 1) точне співпадіння (без регістру)
        for wt in ALL_WORK_TYPES:
            if wt.lower() == raw_lower:
                return wt
        # 2) часткове співпадіння — найдовший збіг ключових слів
        best_match = None
        best_score = 0
        for wt in ALL_WORK_TYPES:
            wt_words = set(wt.lower().split())
            raw_words = set(raw_lower.split())
            common = wt_words & raw_words
            # рахуємо тільки змістовні слова (>=4 символи)
            score = sum(len(w) for w in common if len(w) >= 4)
            if score > best_score:
                best_score = score
                best_match = wt
        if best_match and best_score >= 4:
            logger.info("Нормалізував '%s' → '%s'", raw, best_match)
            return best_match
        return OTHER_WORK_TYPE

    @staticmethod
    def _fallback(reason: str) -> CallAnalysis:
        """Якщо LLM не впорався — мінімально валідний обʼєкт, помічений як проблемний."""
        return CallAnalysis(
            call_type="Інше",
            phone="", branch="", manager="",
            greeting=0, asked_body=0, asked_year=0, asked_mileage=0,
            offered_complex_diag=0, asked_previous_works=0,
            farewell=0, followed_top100_instructions=0,
            appointment_date="",
            work_type=OTHER_WORK_TYPE,
            missed_recommendations="",
            result="Інше",
            parts="",
            score=0,
            comment=f"[АВТО-ФОЛБЕК] {reason}",
            is_problematic=True,
        )

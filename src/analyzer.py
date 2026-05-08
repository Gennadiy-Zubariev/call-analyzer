"""Аналіз транскриптів дзвінків через локальний Ollama."""
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


# ============================================================================
# СИСТЕМНА ЧАСТИНА (system message)
# ============================================================================

SYSTEM_PROMPT = """Ти — досвідчений аудитор якості клієнтського сервісу автосервісу СТО.
Твоє завдання — аналізувати транскрипти телефонних дзвінків між менеджером і клієнтом
та оцінювати якість обслуговування за чіткими критеріями.

КЛЮЧОВІ ПРИНЦИПИ АНАЛІЗУ:

1. Ти оцінюєш ФАКТИ з розмови, а не свої припущення. Якщо інформації немає в
   транскрипті — став 0/false, не вгадуй.

2. ВАЖЛИВО: Інформація вважається "дізнаною менеджером", якщо вона прозвучала
   в розмові — НЕЗАЛЕЖНО від того, хто її озвучив (менеджер запитав чи клієнт
   сам сказав). Менеджер міг просто не перепитувати очевидне.
   Приклад: якщо клієнт одразу сказав "у мене BMW F30 2014 року" — це означає,
   що менеджер знає і марку, і рік. Бали ставимо як за виконане (asked_body=1,
   asked_year=1).

3. Розпізнавай ТИП ДЗВІНКА перш ніж оцінювати:
   - SALES (нове звернення клієнта про послугу) — оцінюй ВСІ критерії
   - FOLLOW-UP (обговорення вже існуючого замовлення, статус робіт) —
     більшість sales-критеріїв НЕ ЗАСТОСОВНІ, став 0 і поясни в comment
   - КОНФЛІКТ/СКАРГА — sales-критерії НЕ ЗАСТОСОВНІ, is_problematic=true

4. Будь ЧЕСНИМ: якщо менеджер реально щось не зробив — фіксуй 0. Якщо зробив —
   фіксуй 1. Не "натягуй" оцінки в обидва боки.

Відповідай СТРОГО у форматі JSON, без додаткового тексту, без markdown."""


# ============================================================================
# КОРИСТУВАЦЬКА ЧАСТИНА (user message) — ШАБЛОН
# ============================================================================

USER_TEMPLATE = """Проаналізуй транскрипт телефонної розмови менеджера СТО з клієнтом.

═══════════════════════════════════════════════════════════════════
ТРАНСКРИПТ:
═══════════════════════════════════════════════════════════════════

{transcript}

═══════════════════════════════════════════════════════════════════
ПОЛЯ JSON ДЛЯ ЗАПОВНЕННЯ:
═══════════════════════════════════════════════════════════════════

## БЛОК 1: ІДЕНТИФІКАЦІЯ

**call_type** — оберіть один з: {call_types}
   - "Вхідний дзвінок" — клієнт телефонує в СТО (за замовчуванням)
   - "Авто в роботі" — обговорення вже виконуваних робіт
   - "Консультація" — клієнт питає поради без запису
   - "Пропущений" — пропущений дзвінок
   - "Інше" — конфлікт, скарга

**phone** — номер телефону клієнта (рядок), або "" якщо не згадувався.

**branch** — філія СТО, якщо згадується. Інакше "".

**manager** — імʼя менеджера. Шукай маркери:
   - "Доброго дня, менеджер [ІМ'Я]"
   - "Це [ІМ'Я], слухаю"
   - НЕ плутай з іменем клієнта!
   Якщо не представився — "".


## БЛОК 2: БІНАРНІ КРИТЕРІЇ (значення 0 або 1)

**greeting** (0/1):
   1 — менеджер привітався І представився ("Доброго дня, менеджер Олег")
   1 — або привітався І назвав СТО ("Доброго дня, СТО АвтоПлюс")
   0 — просто "алло" або "слухаю" без представлення

**asked_body** (0/1):
   1 — у транскрипті прозвучала марка/модель авто (BMW F30, X3, Шкода Октавія)
   0 — модель не згадувалась
   ВАЖЛИВО: ставити 1, навіть якщо клієнт сам її озвучив без запитання!

**asked_year** (0/1):
   1 — у транскрипті є рік випуску ("2014 року", "2011-го", "13-й рік")
   0 — рік не згадувався

**asked_mileage** (0/1):
   1 — у транскрипті є пробіг ("194 тисячі", "250-280", "великий пробіг")
   0 — пробіг не обговорювався

**offered_complex_diag** (0/1):
   1 — менеджер пропонував комплексну діагностику з ціною/умовами
       Маркери: "комплексна діагностика 700 грн", "можемо зробити повну
       діагностику", "рекомендую перевірити все", "комплексна 800 без копії"
   0 — не пропонував активно (якщо клієнт сам спитав — теж 0)

**asked_previous_works** (0/1):
   1 — менеджер питав про попередні роботи / стан авто
       Маркери: "що з машиною робили востаннє?", "які регламентні роботи?",
       "по двигуну що робилось?", "коли востаннє в сервісі були?"
   0 — не цікавився історією обслуговування

**farewell** (0/1):
   1 — менеджер коректно завершив розмову ("До побачення", "Дякую, до зв'язку")
   0 — обірваний кінець або тільки клієнт попрощався

**followed_top100_instructions** (0/1):
   1 — менеджер дотримувався скрипту (вітався, питав про авто, пропонував
       діагностику, фіксував запис) — мінімум 5 з 7 пунктів вище
   0 — порушив скрипт у багатьох місцях


## БЛОК 3: ТЕКСТОВІ ПОЛЯ

**appointment_date** — дата запису або "":
   Формат вільний: "16.07.2025", "середа на 10:00", "через тиждень середа"
   "" — якщо клієнт не записався на конкретний час

**work_type** — оберіть НАЙБЛИЖЧИЙ тип з допустимого списку:
{work_types}

   Алгоритм вибору:
   1. Прочитай суть звернення клієнта
   2. Знайди у списку найточнішу відповідність
   3. ТІЛЬКИ ЯКЩО жоден тип не підходить — "{other_work_type}"
   4. Приклади маппінгу:
      - "поміняти фари" → шукай "Заміна оптики/фар" або найближче
      - "тече масло, не вимірює рівень" → "Діагностика двигуна"
      - "замінити бензобак" → "Заміна бензобака" або найближче
      - "кнопка багажника + діагностика" → "Комплексна діагностика"

**missed_recommendations** — конкретні порушення скрипту, або "":
   Приклади: "Не представився; Не запропонував діагностику"
   "Не уточнив пробіг; Не зафіксував дату запису"

**result** — оберіть один з: {results}

**parts** — оберіть один з: {parts_options}
   - "Клієнта" — клієнт привозить свої / просить замовити для нього
   - "Наші" — сервіс ставить свої запчастини
   - "" — не обговорювалось

**score** (1-10) — загальна оцінка менеджера:
   9-10 — все ідеально, скрипт виконано
   7-8 — невеликі недоліки
   5-6 — виконано лише частину скрипту
   3-4 — значні порушення
   1-2 — критичні проблеми

**comment** — резюме (1-2 речення):
   Що відбулось і ключові недоліки/плюси менеджера.

**is_problematic** (true/false):
   true — конфлікт, скарга, відмова клієнта, серйозні порушення менеджера
   false — нормальна робоча розмова


═══════════════════════════════════════════════════════════════════
ПРИКЛАДИ АНАЛІЗУ (FEW-SHOT):
═══════════════════════════════════════════════════════════════════

### ПРИКЛАД 1: Sales call — успішний запис
Транскрипт: "Доброго дня, менеджер Олег. — Добрий день. — Яка модель?
— BMW X3 2011 року. — Який пробіг? — 250 тисяч. — Що робили востаннє?
— Не пам'ятаю. — Комплексна діагностика 700 грн. Записати? — Так,
на середу 16-го о 10:00. — Записав. До побачення."

JSON:
{{
  "call_type": "Вхідний дзвінок",
  "phone": "",
  "branch": "",
  "manager": "Олег",
  "greeting": 1,
  "asked_body": 1,
  "asked_year": 1,
  "asked_mileage": 1,
  "offered_complex_diag": 1,
  "asked_previous_works": 1,
  "farewell": 1,
  "followed_top100_instructions": 1,
  "appointment_date": "16.07 10:00",
  "work_type": "Комплексна діагностика",
  "missed_recommendations": "",
  "result": "Запис на сервіс",
  "parts": "",
  "score": 9,
  "comment": "Менеджер виконав повний скрипт, успішно записав клієнта.",
  "is_problematic": false
}}

### ПРИКЛАД 2: Конфліктний дзвінок
Транскрипт: "Доброго дня, менеджер Олег. — Чому ви не подзвонили що там
задіри? Зробили все без узгодження, тепер хочете 5000 грн!"

JSON:
{{
  "call_type": "Інше",
  "phone": "",
  "branch": "",
  "manager": "Олег",
  "greeting": 1,
  "asked_body": 0,
  "asked_year": 0,
  "asked_mileage": 0,
  "offered_complex_diag": 0,
  "asked_previous_works": 0,
  "farewell": 1,
  "followed_top100_instructions": 0,
  "appointment_date": "",
  "work_type": "{other_work_type}",
  "missed_recommendations": "Конфліктна ситуація через несвоєчасне інформування клієнта про знахідки",
  "result": "Інше",
  "parts": "",
  "score": 3,
  "comment": "Не sales-дзвінок, скарга клієнта на несвоєчасне інформування про додаткові роботи.",
  "is_problematic": true
}}

═══════════════════════════════════════════════════════════════════
ВИВЕДИ ТІЛЬКИ JSON ДЛЯ ПОТОЧНОГО ТРАНСКРИПТУ (без markdown, без коментарів):
═══════════════════════════════════════════════════════════════════
"""


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
        """Аналізує транскрипт і повертає заповнену картку дзвінка."""
        if not transcript.strip():
            return self._fallback("Транскрипт порожній")

        user_msg = USER_TEMPLATE.format(
            transcript=transcript,
            call_types=" / ".join(CALL_TYPES),
            work_types="\n".join(f"   - {wt}" for wt in ALL_WORK_TYPES),
            results=" / ".join(RESULTS),
            parts_options=" / ".join(repr(p) for p in PARTS_OPTIONS),
            other_work_type=OTHER_WORK_TYPE,
        )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw = self._call_ollama(user_msg)
                data = self._extract_json(raw)
                analysis = CallAnalysis(**data)
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
                "temperature": 0.1,
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
        for wt in ALL_WORK_TYPES:
            if wt.lower() == raw_lower:
                return wt
        best_match = None
        best_score = 0
        for wt in ALL_WORK_TYPES:
            wt_words = set(wt.lower().split())
            raw_words = set(raw_lower.split())
            common = wt_words & raw_words
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
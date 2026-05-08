from __future__ import annotations

import logging
import string
from datetime import datetime
from typing import TYPE_CHECKING

import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import (
    CellFormat, Color, TextFormat,
    format_cell_ranges, set_frozen,
)

from config import (
    BINARY_COLUMN_INDEXES, HEADER_GROUPS, SHEET_HEADERS,
)

if TYPE_CHECKING:
    from src.analyzer import CallAnalysis

logger = logging.getLogger(__name__)

RED_BG = CellFormat(backgroundColor=Color(1.0, 0.85, 0.85))
HEADER_FMT = CellFormat(
    backgroundColor=Color(0.85, 0.85, 0.85),
    textFormat=TextFormat(bold=True),
)


def col_letter(index_zero_based: int) -> str:
    """0 → A, 25 → Z, 26 → AA. Працює до колонки ZZ."""
    n = index_zero_based
    if n < 26:
        return string.ascii_uppercase[n]
    first = string.ascii_uppercase[n // 26 - 1]
    second = string.ascii_uppercase[n % 26]
    return first + second


class SheetsClient:
    def __init__(self, credentials: Credentials) -> None:
        self.gc = gspread.authorize(credentials)
        self._creds = credentials


    def open_sheet(self, sheet_id: str) -> gspread.Worksheet:
        return self.gc.open_by_key(sheet_id).sheet1

    def ensure_headers(self, sheet_id: str) -> None:
        """Записує двохрядковий заголовок (group + поле) якщо його ще нема."""
        ws = self.open_sheet(sheet_id)
        existing = ws.row_values(2)  # перевіряємо саме другий рядок
        if existing and any(cell.strip() for cell in existing):
            logger.info("Заголовки вже є — пропускаю")
            return

        # Row 1 — групи, з повторами для merge
        row1: list[str] = []
        for group_name, span in HEADER_GROUPS:
            row1.extend([group_name] * span)
        # Row 2 — реальні назви полів
        row2 = SHEET_HEADERS

        ws.update(values=[row1, row2], range_name="A1")

        # Форматуємо обидва рядки як шапку
        last_col = col_letter(len(SHEET_HEADERS) - 1)
        format_cell_ranges(ws, [(f"A1:{last_col}2", HEADER_FMT)])

        # Мерджимо клітинки груп (через Sheets API напряму через gspread)
        self._merge_header_groups(ws)

        # Заморожуємо обидва рядки заголовків
        set_frozen(ws, rows=2)

        logger.info("Записано заголовки таблиці")

    def _merge_header_groups(self, ws: gspread.Worksheet) -> None:
        """Обʼєднує клітинки в row 1 для кожної групи, де span > 1."""
        col_idx = 0
        merge_requests = []
        for group_name, span in HEADER_GROUPS:
            if span > 1:
                merge_requests.append({
                    "mergeCells": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + span,
                        },
                        "mergeType": "MERGE_ALL",
                    }
                })
            col_idx += span

        if merge_requests:
            ws.spreadsheet.batch_update({"requests": merge_requests})

    def append_call_row(
        self,
        sheet_id: str,
        date: datetime,
        analysis: "CallAnalysis",
        transcript: str = "",
    ) -> int:
        """Дописує рядок з результатами аналізу. Повертає номер доданого рядка."""
        ws = self.open_sheet(sheet_id)

        # Рядок будуємо рівно по SHEET_HEADERS (22 поля)
        row = [
            date.strftime("%d.%m.%Y"),                       # A: Дата
            transcript,                                      # B: Транскрибація  ← НОВЕ ПОЛЕ
            analysis.call_type,                              # C: Тип звернення
            analysis.phone,                                  # D: Номер телефону
            analysis.branch,                                 # E: Філія
            analysis.manager,                                # F: Менеджер
            analysis.greeting,                               # G: Початок розмови
            analysis.asked_body,                             # H: Кузов
            analysis.asked_year,                             # I: Рік
            analysis.asked_mileage,                          # J: Пробіг
            analysis.offered_complex_diag,                   # K: Комплексна діагностика
            analysis.asked_previous_works,                   # L: Попередні роботи
            analysis.appointment_date,                       # M: Запис на сервіс, Дата
            analysis.farewell,                               # N: Прощання
            analysis.work_type,                              # O: Робота з топ-100
            analysis.followed_top100_instructions,           # P: Дотримувався інструкцій
            analysis.missed_recommendations,                 # Q: Які рекомендації пропущені
            analysis.result,                                 # R: Результат
            analysis.score,                                  # S: Оцінка
            analysis.parts,                                  # T: Запчастини
            analysis.comment,                                # U: Коментар
            analysis.total_score,                            # V: Сума балів
        ]
        assert len(row) == len(SHEET_HEADERS), (
            f"Розбіжність: рядок має {len(row)} полів, а заголовків {len(SHEET_HEADERS)}"
        )

        ws.append_row(row, value_input_option="USER_ENTERED")
        new_row_num = len(ws.get_all_values())

        # Якщо проблемний — фарбуємо рядок червоним
        if analysis.is_problematic:
            self._highlight_row_red(ws, new_row_num)

        logger.info(
            "Записано рядок %d: %s | бал=%d | тип='%s' | проблема=%s",
            new_row_num, analysis.call_type, analysis.total_score,
            analysis.work_type, analysis.is_problematic,
        )
        return new_row_num
    
    @staticmethod
    def _highlight_row_red(ws: gspread.Worksheet, row_num: int) -> None:
        last_col = col_letter(len(SHEET_HEADERS) - 1)
        cell_range = f"A{row_num}:{last_col}{row_num}"
        format_cell_ranges(ws, [(cell_range, RED_BG)])

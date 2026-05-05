"""Google Sheets: створення таблиці, заголовки, дописування, форматування."""
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

from config import BINARY_COLUMN_INDEXES, HEADER_GROUPS, SHEET_HEADERS

if TYPE_CHECKING:
    from src.analyzer import CallAnalysis

logger = logging.getLogger(__name__)

RED_BG = CellFormat(backgroundColor=Color(1.0, 0.85, 0.85))
HEADER_FMT = CellFormat(
    backgroundColor=Color(0.85, 0.85, 0.85),
    textFormat=TextFormat(bold=True),
)


def col_letter(index_zero_based: int) -> str:
    """Перетворює 0-based індекс у літеру колонки (0->A, 25->Z, 26->AA)."""
    # TODO:
    # n = index
    # if n < 26: return ascii_uppercase[n]
    # else: дві літери
    raise NotImplementedError


class SheetsClient:
    def __init__(self, credentials: Credentials) -> None:
        # TODO: self.gc = gspread.authorize(credentials)
        raise NotImplementedError

    def create_work_sheet(self, title: str | None = None) -> str:
        """Створює нову таблицю. Повертає її ID."""
        # TODO:
        # 1. title = title or f"Звіт прослуханих розмов — {datetime.now():%Y-%m-%d}"
        # 2. sh = self.gc.create(title)
        # 3. logger.info(...)
        # 4. return sh.id
        raise NotImplementedError

    def open_sheet(self, sheet_id: str) -> gspread.Worksheet:
        """Відкриває першу вкладку таблиці."""
        # TODO: self.gc.open_by_key(sheet_id).sheet1
        raise NotImplementedError

    def ensure_headers(self, sheet_id: str) -> None:
        """Записує двохрядкові заголовки, якщо їх ще нема."""
        # TODO:
        # 1. ws = self.open_sheet(sheet_id)
        # 2. перевірити row 2 — якщо порожній, продовжити, інакше return
        # 3. сформувати row1 з HEADER_GROUPS (повтори по span)
        # 4. row2 = SHEET_HEADERS
        # 5. ws.update(values=[row1, row2], range_name="A1")
        # 6. format_cell_ranges заголовків
        # 7. self._merge_header_groups(ws)
        # 8. set_frozen(ws, rows=2)
        raise NotImplementedError

    def _merge_header_groups(self, ws: gspread.Worksheet) -> None:
        """Обʼєднує клітинки в row 1 для груп зі span > 1."""
        # TODO:
        # 1. ітеруємо HEADER_GROUPS, накопичуємо merge_requests
        # 2. для кожної групи span > 1 — додаємо merge request
        # 3. ws.spreadsheet.batch_update({"requests": merge_requests})
        raise NotImplementedError

    def append_call_row(
        self,
        sheet_id: str,
        date: datetime,
        analysis: "CallAnalysis",
    ) -> int:
        """Дописує рядок з результатами аналізу. Повертає номер рядка."""
        # TODO:
        # 1. ws = self.open_sheet(sheet_id)
        # 2. зібрати row рівно по порядку SHEET_HEADERS (21 значення)
        # 3. assert len(row) == len(SHEET_HEADERS)
        # 4. ws.append_row(row, value_input_option="USER_ENTERED")
        # 5. new_row_num = len(ws.get_all_values())
        # 6. якщо analysis.is_problematic -> self._highlight_row_red(ws, new_row_num)
        # 7. logger.info(...)
        # 8. return new_row_num
        raise NotImplementedError

    @staticmethod
    def _highlight_row_red(ws: gspread.Worksheet, row_num: int) -> None:
        """Фарбує весь рядок у блідо-червоний."""
        # TODO:
        # 1. last_col = col_letter(len(SHEET_HEADERS) - 1)
        # 2. cell_range = f"A{row_num}:{last_col}{row_num}"
        # 3. format_cell_ranges(ws, [(cell_range, RED_BG)])
        raise NotImplementedError

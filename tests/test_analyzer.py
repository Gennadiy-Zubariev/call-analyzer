"""Тести парсингу LLM-відповіді і нормалізації типу робіт."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer import CallAnalysis, OllamaAnalyzer


def _valid_payload(**overrides):
    """Базовий валідний словник для CallAnalysis."""
    base = dict(
        call_type="Консультація",
        phone="0671234567",
        branch="ОДС",
        manager="Віктор",
        greeting=1, asked_body=1, asked_year=0, asked_mileage=1,
        offered_complex_diag=0, asked_previous_works=1,
        farewell=1, followed_top100_instructions=1,
        appointment_date="14.09 12:00",
        work_type="Заміна оливи ДВЗ + масляний фільтр",
        missed_recommendations="",
        result="Запис",
        parts="Наші",
        score=8,
        comment="Все добре",
        is_problematic=False,
    )
    base.update(overrides)
    return base


def test_total_score_sums_8_binary_fields():
    a = CallAnalysis(**_valid_payload())
    # 1+1+0+1+0+1+1+1 = 6
    assert a.total_score == 6


def test_total_score_max():
    a = CallAnalysis(**_valid_payload(
        greeting=1, asked_body=1, asked_year=1, asked_mileage=1,
        offered_complex_diag=1, asked_previous_works=1,
        farewell=1, followed_top100_instructions=1,
    ))
    assert a.total_score == 8


def test_normalize_work_type_exact_match():
    assert OllamaAnalyzer._normalize_work_type("Комплексна діагностика") == "Комплексна діагностика"


def test_normalize_work_type_case_insensitive():
    assert OllamaAnalyzer._normalize_work_type("комплексна ДІАГНОСТИКА") == "Комплексна діагностика"


def test_normalize_work_type_partial_match():
    # "заміна оливи" має зматчитись з "Заміна оливи ДВЗ + масляний фільтр" або "Заміна оливи АКПП"
    result = OllamaAnalyzer._normalize_work_type("заміна оливи в двигуні")
    assert "Заміна оливи" in result


def test_normalize_work_type_no_match_returns_other():
    assert OllamaAnalyzer._normalize_work_type("щось зовсім інше xyz") == "інший варіант"


def test_normalize_work_type_empty():
    assert OllamaAnalyzer._normalize_work_type("") == "інший варіант"


def test_extract_json_with_markdown_wrapper():
    raw = '```json\n{"foo": "bar"}\n```'
    assert OllamaAnalyzer._extract_json(raw) == {"foo": "bar"}


def test_extract_json_with_extra_text():
    raw = 'Ось JSON: {"foo": "bar"} і ще щось'
    assert OllamaAnalyzer._extract_json(raw) == {"foo": "bar"}


def test_fallback_is_problematic():
    fb = OllamaAnalyzer._fallback("test reason")
    assert fb.is_problematic is True
    assert "test reason" in fb.comment
    assert fb.work_type == "інший варіант"
    assert fb.total_score == 0

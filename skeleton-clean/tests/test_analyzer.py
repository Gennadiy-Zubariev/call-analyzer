"""Юніт-тести парсингу LLM-відповіді і нормалізації типу робіт.

Запуск: pytest tests/ -v
"""
from __future__ import annotations


def test_total_score_sums_8_binary_fields():
    """Сума 8 бінарних полів = total_score."""
    # TODO: створити CallAnalysis з відомими бінарниками, перевірити суму
    pass


def test_normalize_work_type_exact_match():
    """Точна назва зі списку повертається як є."""
    # TODO
    pass


def test_normalize_work_type_partial_match():
    """Часткове співпадіння знаходить найкращий варіант."""
    # TODO
    pass


def test_normalize_work_type_no_match_returns_other():
    """Якщо нічого не підходить — 'інший варіант'."""
    # TODO
    pass


def test_extract_json_with_markdown_wrapper():
    """Парсимо JSON навіть якщо обгорнутий у ```json ... ```."""
    # TODO
    pass


def test_fallback_is_problematic():
    """Фолбек має бути помічений як проблемний."""
    # TODO
    pass

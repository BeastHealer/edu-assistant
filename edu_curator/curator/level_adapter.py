"""Постобработка ответа под уровень студента (страховка поверх LLM)."""

from __future__ import annotations

import re

from edu_curator.models import StudentLevel

ADVANCED_TERMS = {
    "асимптотик": "поведение на больших числах",
    "кросс-валидац": "проверка модели на нескольких разбиениях данных",
    "регуляризац": "штраф за слишком сложную модель",
}


def simplify_for_beginner(text: str) -> str:
    result = text
    replacements = [
        (r"\bEDA\b", "EDA (исследовательский анализ данных)"),
        (r"\bbaseline\b", "baseline (простая опорная модель)"),
        (r"\bIQR\b", "IQR (размах между квартилями)"),
    ]
    for pattern, repl in replacements:
        if re.search(pattern, result) and repl.split(" (")[0] not in result:
            result = re.sub(pattern, repl, result, count=1)
    return result


def adapt_answer(text: str, level: StudentLevel) -> str:
    if level == StudentLevel.BEGINNER:
        return simplify_for_beginner(text)
    return text

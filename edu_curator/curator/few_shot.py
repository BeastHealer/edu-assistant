"""Загрузка few-shot примеров в промпт."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from config import settings
from edu_curator.models import Scenario, StudentLevel


@lru_cache(maxsize=1)
def load_examples(path: str | None = None) -> dict:
    file_path = Path(path) if path else settings.few_shot_path
    return json.loads(file_path.read_text(encoding="utf-8"))


def format_few_shot_block(
    scenario: Scenario,
    level: StudentLevel,
    *,
    max_correct: int = 2,
    max_incorrect: int = 1,
) -> str:
    data = load_examples()
    correct_sorted = sorted(
        data.get("correct", []),
        key=lambda x: (
            0 if x.get("scenario") == scenario.value else 1,
            0 if x.get("level") == level.value else 1,
        ),
    )[:max_correct]
    incorrect_sorted = sorted(
        data.get("incorrect", []),
        key=lambda x: 0 if x.get("scenario") == scenario.value else 1,
    )[:max_incorrect]

    lines = ["Примеры (few-shot). Повторяй паттерн корректных, избегай некорректных."]
    for item in correct_sorted:
        lines.append(
            f"\nКОРРЕКТНО [{item['id']}, {item['scenario']}, {item['level']}]\n"
            f"Вопрос: {item['question']}\n"
            f"Ответ: {item['answer']}\n"
            f"Почему это хорошо: {item['why_correct']}"
        )
    for item in incorrect_sorted:
        lines.append(
            f"\nНЕКОРРЕКТНО [{item['id']}]\n"
            f"Вопрос: {item['question']}\n"
            f"Плохой ответ: {item['answer']}\n"
            f"Почему нельзя: {item['why_incorrect']}"
        )
    return "\n".join(lines)

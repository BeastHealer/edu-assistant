"""Маршрутизация сценария по вопросу студента."""

from __future__ import annotations

import re

from edu_curator.models import Scenario

CONSTRAINT_PATTERNS = [
    r"постав(ь|ьте).*(оценк|зач[её]т|балл)",
    r"(какую|какая) оценк",
    r"перенес(и|ите)|подвинь|продл(и|ите)|сдвинь.*дедлайн",
    r"поставь.*зач[её]т",
    r"напиши.*(готовое|решение|код).*(дз|домашк|проект)",
    r"сделай за меня",
    r"скинь готовый ноутбук",
]

DEADLINE_KEYWORDS = [
    "дедлайн",
    "срок",
    "когда сда",
    "до какого",
    "расписан",
    "вебинар",
    "защит",
    "продлен",
    "перенос",
    "посещаем",
    "мягк",
]

DIFFICULTY_KEYWORDS = [
    "сложно",
    "не понимаю",
    "ничего не понял",
    "не тяну",
    "трудно",
    "слишком тяжел",
    "паникую",
    "не туда попал",
    "не справляюсь",
    "голова кипит",
]

RECOMMENDATION_KEYWORDS = [
    "порекоменд",
    "что почитать",
    "доп",
    "дополнительн",
    "ресурсы",
    "с чего начать",
    "траектори",
    "что ещё",
    "материалы сверх",
]

ASSIGNMENT_KEYWORDS = [
    "дз",
    "домашк",
    "задан",
    "проект",
    "ноутбук",
    "groupby",
    "как сделать",
    "подскаж",
    "критери",
    "сдать",
    "черновик",
]

TECHNICAL_KEYWORDS = [
    "установ",
    "jupyter",
    "ошибк",
    "encoding",
    "кодиров",
    "не открыва",
    "парол",
    "доступ",
    "colab",
    "import",
    "модуль не найден",
    "kernel",
    "ядро",
]

MOTIVATION_KEYWORDS = [
    "как учиться",
    "выгорел",
    "мотивац",
    "сколько часов",
    "темп",
    "ритм",
    "пропустить модуль",
]

CONCEPT_KEYWORDS = [
    "что такое",
    "объясни",
    "корреляц",
    "переобучен",
    "медиана",
    "pandas",
    "train",
    "тест",
    "метрик",
    "чем отличается",
    "зачем нужен",
]


def _contains(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def classify_scenario(question: str) -> Scenario:
    q = question.lower().strip()
    if not q:
        return Scenario.GENERAL

    for pattern in CONSTRAINT_PATTERNS:
        if re.search(pattern, q):
            return Scenario.CONSTRAINT

    scores: dict[Scenario, int] = {
        Scenario.DEADLINE: sum(1 for k in DEADLINE_KEYWORDS if k in q),
        Scenario.DIFFICULTY: sum(1 for k in DIFFICULTY_KEYWORDS if k in q),
        Scenario.RECOMMENDATION: sum(1 for k in RECOMMENDATION_KEYWORDS if k in q),
        Scenario.ASSIGNMENT_HELP: sum(1 for k in ASSIGNMENT_KEYWORDS if k in q),
        Scenario.TECHNICAL: sum(1 for k in TECHNICAL_KEYWORDS if k in q),
        Scenario.MOTIVATION: sum(1 for k in MOTIVATION_KEYWORDS if k in q),
        Scenario.CONCEPT: sum(1 for k in CONCEPT_KEYWORDS if k in q),
    }

    if scores[Scenario.DIFFICULTY] and scores[Scenario.CONCEPT]:
        return Scenario.DIFFICULTY
    if scores[Scenario.DEADLINE] and re.search(r"постав|оценк|зач[её]т", q):
        return Scenario.CONSTRAINT

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return Scenario.GENERAL
    return best


def retrieval_hint(scenario: Scenario) -> str:
    """Добавка к поисковому запросу, чтобы подтянуть нужный тип ресурса."""
    return {
        Scenario.DEADLINE: "дедлайн домашнее задание FAQ",
        Scenario.DIFFICULTY: "сложность как учиться методичка",
        Scenario.RECOMMENDATION: "рекомендованные дополнительные ресурсы",
        Scenario.ASSIGNMENT_HELP: "методичка домашнее задание критерии",
        Scenario.TECHNICAL: "Jupyter установка FAQ технические",
        Scenario.MOTIVATION: "как учиться ритм методичка",
        Scenario.CONSTRAINT: "оценки дедлайны полномочия куратора FAQ",
        Scenario.CONCEPT: "лекция определение",
        Scenario.GENERAL: "",
    }[scenario]


SCENARIO_RESOURCE_HINT = {
    Scenario.DEADLINE: "faq",
    Scenario.TECHNICAL: "faq",
    Scenario.RECOMMENDATION: "extra",
    Scenario.ASSIGNMENT_HELP: "methodic",
    Scenario.MOTIVATION: "methodic",
    Scenario.CONSTRAINT: "faq",
}

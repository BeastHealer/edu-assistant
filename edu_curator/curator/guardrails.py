"""Гардрейлы: повторная проверка ответа куратора."""

from __future__ import annotations

import re

from edu_curator.models import Scenario

FORBIDDEN_GRADE = [
    r"ставлю тебе",
    r"оценка[: ]+\d",
    r"получишь \d",
    r"зачту как",
    r"ставлю зач[её]т",
    r"\b\d{1,2} из 10\b",
]

FORBIDDEN_SCHEDULE = [
    r"я перенёс",
    r"я перенес",
    r"дедлайн теперь",
    r"продлеваю",
    r"можно сдать когда удобно",
]


def looks_like_full_solution(question: str, answer: str) -> bool:
    q = question.lower()
    wants_code = any(w in q for w in ["напиши код", "готовое решение", "скинь код", "сделай дз"])
    code_lines = len(re.findall(r"^\s*(df\.|import |from |plt\.)", answer, re.M))
    return wants_code and code_lines >= 3


def scan_violations(answer: str, scenario: Scenario) -> list[str]:
    text = answer.lower()
    issues: list[str] = []
    for pat in FORBIDDEN_GRADE:
        if re.search(pat, text):
            issues.append("grade")
            break
    for pat in FORBIDDEN_SCHEDULE:
        if re.search(pat, text):
            issues.append("schedule")
            break
    if scenario == Scenario.CONSTRAINT and re.search(r"хорошо, перенес", text):
        issues.append("schedule")
    return issues


SAFE_FALLBACK = (
    "Этот запрос вне полномочий ИИ-куратора. Я не выставляю оценки и не меняю расписание — "
    "это делает преподаватель в LMS. Могу помочь разобрать материал курса, критерии задания "
    "или указать источник в базе знаний. Напишите, пожалуйста, учебный или организационный вопрос, "
    "на который можно ответить по лекциям, методичкам или FAQ."
)

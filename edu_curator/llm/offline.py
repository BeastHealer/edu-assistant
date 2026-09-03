"""Офлайн-синтезатор ответа по RAG-контексту.

Работает без API-ключа: извлекает релевантные абзацы, применяет
сценарий/уровень и гардрейлы. Демонстрирует ту же архитектуру промптов.
"""

from __future__ import annotations

import re

from edu_curator.models import RetrievedChunk, Scenario, StudentLevel
from edu_curator.rag.context import format_sources_footer

OPENINGS = {
    StudentLevel.BEGINNER: {
        Scenario.DIFFICULTY: "Это нормально — тема правда может казаться тяжёлой на старте. Давайте сузим шаг.",
        Scenario.MOTIVATION: "Давайте соберём спокойный ритм, без гонки за всеми доп. материалами сразу.",
        Scenario.CONSTRAINT: "Этот запрос я выполнить не могу — у куратора нет таких полномочий.",
        Scenario.DEADLINE: "Сверяюсь только с расписанием LMS, куратор сроки не двигает.",
        Scenario.ASSIGNMENT_HELP: "Помогу разобрать постановку и куда смотреть, но готовое решение ДЗ не пишу.",
        Scenario.RECOMMENDATION: "Сначала обязательный материал недели, потом точечные доп. ресурсы под ваш уровень.",
        Scenario.TECHNICAL: "Идём по короткому чеклисту из технического FAQ.",
        Scenario.CONCEPT: "Объясню простыми словами и привяжу к лекции курса.",
        Scenario.GENERAL: "Опираюсь на материалы курса и FAQ.",
    },
    StudentLevel.ADVANCED: {
        Scenario.DIFFICULTY: "Даже на продвинутом треке имеет смысл сузить вопрос до одного узкого места.",
        Scenario.MOTIVATION: "Имеет смысл оптимизировать время: критерии приёмки важнее дополнительного чтения.",
        Scenario.CONSTRAINT: "Это вне полномочий куратора: оценки и расписание — зона преподавателя/LMS.",
        Scenario.DEADLINE: "Канонические даты — только LMS. Ниже — как они зафиксированы сейчас.",
        Scenario.ASSIGNMENT_HELP: "Разберём критерии и типовые ошибки; полный код сдаваемого пункта не выдаю.",
        Scenario.RECOMMENDATION: "После обязательного минимума модуля можно углубиться точечно.",
        Scenario.TECHNICAL: "Короткий чеклист из FAQ, без сброса доступов.",
        Scenario.CONCEPT: "Краткая выжимка по материалам курса и ограничения интерпретации.",
        Scenario.GENERAL: "По материалам базы знаний и LMS.",
    },
}


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    cleaned: list[str] = []
    for part in parts:
        if part.startswith("---"):
            continue
        lines = [ln.strip() for ln in part.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        para = " ".join(lines).strip()
        if para:
            cleaned.append(para)
    return cleaned


def _overlap_score(query: str, text: str) -> int:
    tokens = [t for t in re.findall(r"[а-яёa-z0-9]{4,}", query.lower())]
    hay = text.lower()
    return sum(1 for t in tokens if t in hay)


def _pick_paragraphs(chunks: list[RetrievedChunk], query: str, limit: int) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for chunk in chunks:
        for para in _paragraphs(chunk.text):
            if len(para) < 40:
                continue
            candidates.append((_overlap_score(query, para + " " + chunk.topic), para))
    candidates.sort(key=lambda x: x[0], reverse=True)
    picked = [p for score, p in candidates if score > 0][:limit]
    if picked:
        return picked
    fallback: list[str] = []
    for chunk in chunks:
        text = chunk.text.strip().replace("\n", " ")
        if text:
            fallback.append(text[:500])
        if len(fallback) >= limit:
            break
    return fallback


def synthesize(
    *,
    question: str,
    scenario: Scenario,
    level: StudentLevel,
    chunks: list[RetrievedChunk],
    lms_facts: str,
) -> str:
    opening = OPENINGS[level][scenario]
    body_limit = 2 if level == StudentLevel.BEGINNER else 3
    paras = [] if scenario == Scenario.CONSTRAINT else _pick_paragraphs(chunks, question, body_limit)

    sections = [opening]
    if paras:
        if level == StudentLevel.BEGINNER:
            sections.append("Коротко по материалам курса:")
            for para in paras:
                sentence = para.split(". ")
                compact = ". ".join(sentence[:2]).strip()
                if compact and not compact.endswith("."):
                    compact += "."
                sections.append(compact)
        else:
            sections.append("По материалам курса:")
            sections.extend(paras)

        if lms_facts.strip() and scenario in {
            Scenario.DEADLINE,
            Scenario.ASSIGNMENT_HELP,
            Scenario.GENERAL,
        }:
            lms_lines = [ln for ln in lms_facts.splitlines() if ln.strip()]
            if scenario == Scenario.DEADLINE:
                keep = [ln for ln in lms_lines if "дедлайн" in ln.lower() or ln.startswith("- HW") or ln.startswith("- PROJ") or "Задания" in ln or "Курс:" in ln]
                if not keep:
                    keep = lms_lines[:12]
                sections.append("Факты из LMS:\n" + "\n".join(keep[:12]))
            else:
                lms_lines = [ln for ln in lms_facts.splitlines() if ln.strip()][:8]
                if lms_lines:
                    sections.append("Факты из LMS:\n" + "\n".join(lms_lines))

    if scenario == Scenario.ASSIGNMENT_HELP:
        sections.append(
            "Следующий шаг: откройте методичку задания, сделайте свою попытку и пришлите фрагмент "
            "с ошибкой — разберём её. Готовый код оцениваемого пункта отправить не могу."
        )
    elif scenario == Scenario.DIFFICULTY:
        sections.append(
            "Следующий шаг: законспектируйте один раздел лекции своими словами (полстраницы) "
            "и напишите, какая именно фраза осталась непонятной."
        )
    elif scenario == Scenario.RECOMMENDATION:
        sections.append(
            "Дополнительные материалы не заменяют сдачу обязательных работ текущей недели."
        )
    elif scenario == Scenario.CONSTRAINT:
        sections.append(
            "Могу вместо этого помочь с содержанием лекции, критериями задания или навигацией по FAQ."
        )

    if not paras and not lms_facts.strip():
        sections.append(
            "В базе знаний не нашлось достаточно близкого фрагмента. Загляните в LMS → материалы "
            "модуля или переформулируйте вопрос (модуль + тема)."
        )

    sections.append(format_sources_footer(chunks))
    return "\n\n".join(sections)


class OfflineSynthesizer:
    backend_name = "offline-rag"

    def generate(self, system_prompt: str, human_prompt: str) -> str:
        # Агент вызывает synthesize() напрямую. Этот метод — запасной.
        return (
            "Офлайн-режим: ответ собирается из найденных фрагментов базы знаний. "
            "Подключите GigaChat в .env для генерации свободным языком.\n\n"
            f"{human_prompt[-1500:]}"
        )

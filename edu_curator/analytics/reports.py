"""Агрегаты для дашборда и текстового отчёта по темам."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import settings


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.analytics_db
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def load_queries(db_path: Path | None = None) -> pd.DataFrame:
    path = db_path or settings.analytics_db
    if not path.exists():
        return pd.DataFrame()
    with _connect(path) as conn:
        df = pd.read_sql_query("SELECT * FROM queries ORDER BY created_at", conn)
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    return df


def explode_topics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["topic", "count"])
    counter: Counter[str] = Counter()
    for raw in df["topics"].fillna("[]"):
        try:
            items = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            items = []
        for item in items or []:
            if item:
                counter[str(item)] += 1
    if not counter:
        return pd.DataFrame(columns=["topic", "count"])
    return (
        pd.DataFrame(counter.items(), columns=["topic", "count"])
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )


def frequent_questions(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if df.empty:
        return df
    copy = df.copy()
    copy["q_norm"] = copy["question"].str.lower().str.strip()
    grouped = (
        copy.groupby("q_norm", as_index=False)
        .agg(count=("id", "size"), sample=("question", "first"), scenario=("scenario", "first"))
        .sort_values("count", ascending=False)
        .head(limit)
    )
    return grouped


def build_markdown_report(df: pd.DataFrame) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if df.empty:
        return f"# Аналитический отчёт по запросам куратора\n\nНет данных на {now}."

    topics = explode_topics(df)
    top_q = frequent_questions(df, 8)
    by_scenario = df["scenario"].value_counts()
    by_level = df["level"].value_counts()
    blocked = int(df["blocked"].sum()) if "blocked" in df else 0

    lines = [
        "# Аналитический отчёт по запросам ИИ-куратора",
        "",
        f"Сформирован: {now}",
        f"Всего запросов: **{len(df)}**",
        f"Заблокировано гардрейлами: **{blocked}**",
        "",
        "## Распределение по сценариям",
    ]
    for name, count in by_scenario.items():
        lines.append(f"- {name}: {count}")
    lines += ["", "## Уровни студентов"]
    for name, count in by_level.items():
        lines.append(f"- {name}: {count}")
    lines += ["", "## Темы, которые спрашивают чаще всего", ""]
    if topics.empty:
        lines.append("Недостаточно тематических меток.")
    else:
        for _, row in topics.head(12).iterrows():
            lines.append(f"- {row['topic']}: {int(row['count'])}")
    lines += ["", "## Повторяющиеся формулировки вопросов", ""]
    for _, row in top_q.iterrows():
        lines.append(f"- ({int(row['count'])}) {row['sample']} — сценарий `{row['scenario']}`")
    lines += [
        "",
        "## Рекомендации команде курса",
        "- Если одна тема лидирует — усилить FAQ или добавить 2-минутный скринкаст.",
        "- Всплеск `difficulty` на модуле M4/M5 — пересмотреть темп лекции и добавить разбор на вебинаре.",
        "- Частые `deadline` — вынести даты на дашборд LMS крупнее, чем в чате.",
        "- Кластер `assignment_help` по одному ДЗ — уточнить формулировку критерия приёмки.",
    ]
    return "\n".join(lines)

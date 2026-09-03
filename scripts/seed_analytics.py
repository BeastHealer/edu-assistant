"""Заполнить аналитику вымышленными запросами, чтобы дашборд был живым."""

from __future__ import annotations

import json
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings  # noqa: E402
from edu_curator.analytics.logger import SCHEMA  # noqa: E402

STUDENTS = [
    ("STU-1001", "Анна П.", "beginner"),
    ("STU-1002", "Дмитрий С.", "advanced"),
    ("STU-1003", "Мария К.", "beginner"),
    ("STU-1004", "Игорь Л.", "advanced"),
    ("STU-1005", "Ольга Н.", "beginner"),
]

SAMPLES = [
    ("Когда дедлайн первого ДЗ?", "deadline", "M2", ["M2", "дедлайны"]),
    ("До какого числа сдавать проект?", "deadline", "M6", ["M6", "дедлайны"]),
    ("Можно ли сдать после дедлайна?", "deadline", "M0", ["организация", "дедлайны"]),
    ("Я ничего не понимаю в корреляции", "difficulty", "M4", ["M4", "корреляция"]),
    ("Слишком сложно, не тяну статистику", "difficulty", "M4", ["M4", "сложность"]),
    ("Что почитать дополнительно по pandas?", "recommendation", "M2", ["M2", "ресурсы"]),
    ("Рекомендуй материалы для продвинутых по ML", "recommendation", "M5", ["M5", "ресурсы"]),
    ("Что такое переобучение?", "concept", "M5", ["M5", "переобучение"]),
    ("Зачем делить на train и test?", "concept", "M5", ["M5", "train/test"]),
    ("Как сделать топ-5 городов в ДЗ-1?", "assignment_help", "M2", ["M2", "ДЗ-1"]),
    ("Какие критерии у итогового проекта?", "assignment_help", "M6", ["M6", "проект"]),
    ("Jupyter не видит pandas", "technical", "M0", ["технические", "Jupyter"]),
    ("Ошибка кодировки CSV", "technical", "M2", ["технические", "CSV"]),
    ("Как учиться, чтобы не выгореть?", "motivation", "M0", ["методичка", "ритм"]),
    ("Поставь мне зачёт", "constraint", "M0", ["ограничения"]),
    ("Перенеси дедлайн на неделю", "constraint", "M0", ["ограничения", "дедлайны"]),
    ("Чем медиана лучше среднего?", "concept", "M4", ["M4", "медиана"]),
    ("Нужно ли ходить на вебинары?", "deadline", "M0", ["организация", "вебинары"]),
    ("Можно сдавать в Colab?", "technical", "M0", ["технические", "Colab"]),
    ("С чего начать, если Python новый?", "recommendation", "M2", ["M2", "новичок"]),
]


def main() -> None:
    random.seed(42)
    db_path = settings.analytics_db
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM queries")

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(96):
        q, scenario, module, topics = SAMPLES[i % len(SAMPLES)]
        student_id, name, level = STUDENTS[i % len(STUDENTS)]
        created = now - timedelta(days=random.randint(0, 21), hours=random.randint(0, 23))
        blocked = 1 if scenario == "constraint" else 0
        rows.append(
            (
                created.isoformat(),
                student_id,
                name,
                q,
                "(демо-лог: ответ опущен)",
                scenario,
                level,
                module,
                "",
                json.dumps(topics, ensure_ascii=False),
                "[]",
                "offline-rag",
                "high",
                blocked,
            )
        )

    conn.executemany(
        """
        INSERT INTO queries (
            created_at, student_id, student_name, question, answer,
            scenario, level, module, resource_type, topics, sources,
            llm_backend, confidence, blocked
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()
    print(f"Записано {len(rows)} учебных событий в {db_path}")


if __name__ == "__main__":
    main()

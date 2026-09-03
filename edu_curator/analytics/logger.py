"""Логирование запросов в SQLite (учебная аналитика, без реальных ПДн)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import settings
from edu_curator.models import CuratorRequest, CuratorResponse


SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    student_id TEXT,
    student_name TEXT,
    question TEXT NOT NULL,
    answer TEXT,
    scenario TEXT,
    level TEXT,
    module TEXT,
    resource_type TEXT,
    topics TEXT,
    sources TEXT,
    llm_backend TEXT,
    confidence TEXT,
    blocked INTEGER DEFAULT 0
);
"""


class QueryLogger:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.analytics_db
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def log(self, request: CuratorRequest, response: CuratorResponse) -> None:
        topics = sorted(
            {chunk.topic for chunk in response.sources if chunk.topic}
            | {chunk.module for chunk in response.sources if chunk.module}
        )
        sources = [
            {
                "doc_id": c.doc_id,
                "source": c.source,
                "module": c.module,
                "resource_type": c.resource_type,
                "score": c.score,
            }
            for c in response.sources
        ]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO queries (
                    created_at, student_id, student_name, question, answer,
                    scenario, level, module, resource_type, topics, sources,
                    llm_backend, confidence, blocked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    request.student_id,
                    request.student_name,
                    request.question,
                    response.answer,
                    response.scenario.value,
                    response.level.value,
                    request.module_filter or (response.sources[0].module if response.sources else ""),
                    request.resource_type_filter or "",
                    json.dumps(topics, ensure_ascii=False),
                    json.dumps(sources, ensure_ascii=False),
                    response.llm_backend,
                    response.confidence,
                    int(response.blocked),
                ),
            )
            conn.commit()

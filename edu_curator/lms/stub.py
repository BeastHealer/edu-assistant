"""Заглушка LMS: чтение JSON/CSV и выгрузки для интеграции."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from config import settings

MSK = ZoneInfo("Europe/Moscow")


class LMSStub:
    """Имитация API учебной платформы. Только учебные данные."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.lms_dir

    def get_schedule(self) -> dict[str, Any]:
        return json.loads((self.root / "schedule.json").read_text(encoding="utf-8"))

    def get_modules(self) -> dict[str, Any]:
        return json.loads((self.root / "modules.json").read_text(encoding="utf-8"))

    def get_students(self) -> dict[str, Any]:
        return json.loads((self.root / "students.json").read_text(encoding="utf-8"))

    def get_assignments(self) -> list[dict[str, str]]:
        with (self.root / "assignments.csv").open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def export_schedule_csv(self) -> str:
        events = self.get_schedule().get("events", [])
        buffer = StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=["id", "type", "module", "title", "starts_at", "ends_at"],
        )
        writer.writeheader()
        for event in events:
            writer.writerow(event)
        return buffer.getvalue()

    def export_assignments_json(self) -> str:
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source": "LMS stub",
            "assignments": self.get_assignments(),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def facts_for_prompt(self, now: datetime | None = None) -> str:
        now = now or datetime.now(MSK)
        lines = [
            f"Сейчас (МСК): {now.strftime('%Y-%m-%d %H:%M')}",
            f"Курс: {self.get_schedule().get('title')} "
            f"({self.get_schedule().get('start')} — {self.get_schedule().get('end')})",
            "Задания и дедлайны (канон LMS):",
        ]
        for hw in self.get_assignments():
            lines.append(
                f"- {hw['assignment_id']} | {hw['module']} | {hw['title']} | "
                f"дедлайн {hw['deadline']} | мягкий {hw['soft_deadline']} | вес {hw['weight']}%"
            )
        lines.append("Ближайшие события:")
        for event in self.get_schedule().get("events", [])[:8]:
            lines.append(
                f"- [{event['module']}] {event['title']} "
                f"{event['starts_at']} ({event['type']})"
            )
        lines.append(
            "Правило: расписание меняет только преподаватель; куратор цитирует LMS, но не редактирует."
        )
        return "\n".join(lines)

    def upcoming_deadlines(self, limit: int = 5) -> list[dict[str, str]]:
        now = datetime.now(MSK)
        items = []
        for hw in self.get_assignments():
            try:
                due = datetime.fromisoformat(hw["deadline"])
            except ValueError:
                continue
            items.append({**hw, "_due": due.isoformat(), "_past": str(due < now)})
        items.sort(key=lambda x: x["deadline"])
        return items[:limit]

"""Общие модели данных куратора."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StudentLevel(str, Enum):
    BEGINNER = "beginner"
    ADVANCED = "advanced"


class Scenario(str, Enum):
    DEADLINE = "deadline"
    DIFFICULTY = "difficulty"
    RECOMMENDATION = "recommendation"
    CONCEPT = "concept"
    ASSIGNMENT_HELP = "assignment_help"
    TECHNICAL = "technical"
    MOTIVATION = "motivation"
    CONSTRAINT = "constraint"
    GENERAL = "general"


class RetrievedChunk(BaseModel):
    text: str
    source: str
    doc_id: str = ""
    module: str = ""
    topic: str = ""
    resource_type: str = ""
    difficulty: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CuratorRequest(BaseModel):
    question: str
    level: StudentLevel = StudentLevel.BEGINNER
    student_id: str = "demo-student"
    student_name: str = "Гость"
    module_filter: str | None = None
    resource_type_filter: str | None = None
    topic_filter: str | None = None
    chat_history: list[dict[str, str]] = Field(default_factory=list)


class CuratorResponse(BaseModel):
    answer: str
    scenario: Scenario
    level: StudentLevel
    sources: list[RetrievedChunk] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""
    llm_backend: str = ""
    confidence: str = "medium"
    retrieved_query: str = ""

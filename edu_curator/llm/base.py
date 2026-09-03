"""Контракт LLM."""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    backend_name: str

    def generate(self, system_prompt: str, human_prompt: str) -> str: ...

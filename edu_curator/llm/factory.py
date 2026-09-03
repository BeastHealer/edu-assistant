"""Выбор LLM: GigaChat → OpenAI-compatible → офлайн RAG-синтезатор."""

from __future__ import annotations

from edu_curator.llm.gigachat_client import try_gigachat
from edu_curator.llm.offline import OfflineSynthesizer
from edu_curator.llm.openai_client import try_openai


def get_llm():
    client = try_gigachat()
    if client:
        return client
    client = try_openai()
    if client:
        return client
    return OfflineSynthesizer()

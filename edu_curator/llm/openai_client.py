"""Опциональный OpenAI-совместимый клиент."""

from __future__ import annotations

import logging

from config import settings

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    backend_name = "openai-compatible"

    def __init__(self) -> None:
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": settings.openai_model,
            "temperature": settings.llm_temperature,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self._model = ChatOpenAI(**kwargs)

    def generate(self, system_prompt: str, human_prompt: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        result = self._model.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        return str(result.content).strip()


def try_openai() -> OpenAICompatibleClient | None:
    if not settings.openai_api_key.strip():
        return None
    try:
        return OpenAICompatibleClient()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenAI-совместимый клиент недоступен: %s", exc)
        return None

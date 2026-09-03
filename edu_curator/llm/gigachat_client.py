"""Клиент GigaChat через LangChain."""

from __future__ import annotations

import logging

from config import settings

logger = logging.getLogger(__name__)


class GigaChatClient:
    backend_name = "gigachat"

    def __init__(self) -> None:
        from langchain_gigachat.chat_models import GigaChat

        self._model = GigaChat(
            credentials=settings.gigachat_credentials,
            scope=settings.gigachat_scope,
            model=settings.gigachat_model,
            verify_ssl_certs=settings.gigachat_verify_ssl_certs,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout,
            profanity_check=False,
        )

    def generate(self, system_prompt: str, human_prompt: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        result = self._model.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        return str(result.content).strip()


def try_gigachat() -> GigaChatClient | None:
    if not settings.gigachat_credentials.strip():
        return None
    try:
        return GigaChatClient()
    except Exception as exc:  # noqa: BLE001
        logger.warning("GigaChat недоступен: %s", exc)
        return None

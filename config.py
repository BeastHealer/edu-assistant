"""Конфигурация ИИ-куратора EduPath."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gigachat_credentials: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat"
    gigachat_verify_ssl_certs: bool = False

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"

    embedding_backend: str = "auto"
    hf_embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    knowledge_dir: Path = ROOT_DIR / "data" / "knowledge"
    chroma_dir: Path = ROOT_DIR / "data" / "chroma"
    analytics_db: Path = ROOT_DIR / "data" / "analytics" / "queries.db"
    lms_dir: Path = ROOT_DIR / "data" / "lms"
    few_shot_path: Path = ROOT_DIR / "data" / "few_shot" / "examples.json"

    chroma_collection: str = "edupath_knowledge"
    retrieval_k: int = 5
    chunk_size: int = 700
    chunk_overlap: int = 120

    curator_name: str = "Алекс"
    course_title: str = "Data Science: от нуля до первого проекта"
    platform_name: str = "EduPath"

    llm_temperature: float = 0.3
    llm_timeout: int = 60


def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""Эмбеддинги: GigaChat → HuggingFace → TF-IDF (всегда доступен офлайн)."""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import Any

import numpy as np
from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from config import settings

logger = logging.getLogger(__name__)


class TfidfEmbeddings(Embeddings):
    """Локальные эмбеддинги без внешних API и без скачивания моделей.

    Векторизатор обучается на корпусе при индексации и сериализуется вместе
    с коллекцией через отдельный pickle на диске (см. indexer).
    Для запросов после fit используется тот же словарь.
    """

    def __init__(self, max_features: int = 4096) -> None:
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            sublinear_tf=True,
            analyzer="char_wb",
            min_df=1,
        )
        self._fitted = False
        self._dim = max_features

    def fit(self, texts: list[str]) -> "TfidfEmbeddings":
        self.vectorizer.fit(texts)
        self._fitted = True
        self._dim = len(self.vectorizer.get_feature_names_out())
        return self

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            self.fit(texts)
        matrix = self.vectorizer.transform(texts)
        dense = normalize(matrix).toarray().astype(np.float32)
        if dense.shape[1] < self.max_features:
            pad = np.zeros((dense.shape[0], self.max_features - dense.shape[1]), dtype=np.float32)
            dense = np.hstack([dense, pad])
        return dense[:, : self.max_features].tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


class HashEmbeddings(Embeddings):
    """Аварийный запасной вариант фиксированной размерности."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            tokens = ["_empty"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm:
            vec /= norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


def _try_gigachat_embeddings() -> Embeddings | None:
    if not settings.gigachat_credentials:
        return None
    try:
        from langchain_gigachat.embeddings import GigaChatEmbeddings

        logger.info("Эмбеддинги: GigaChat")
        return GigaChatEmbeddings(
            credentials=settings.gigachat_credentials,
            scope=settings.gigachat_scope,
            verify_ssl_certs=settings.gigachat_verify_ssl_certs,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("GigaChat embeddings недоступны: %s", exc)
        return None


def _try_hf_embeddings() -> Embeddings | None:
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return None
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        logger.info("Эмбеддинги: HuggingFace %s", settings.hf_embedding_model)
        return HuggingFaceEmbeddings(
            model_name=settings.hf_embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("HuggingFace embeddings недоступны: %s", exc)
        return None


@lru_cache(maxsize=1)
def get_embeddings() -> tuple[Embeddings, str]:
    backend = settings.embedding_backend.lower()
    if backend == "gigachat":
        emb = _try_gigachat_embeddings()
        if emb:
            return emb, "gigachat"
        raise RuntimeError("Запрошены эмбеддинги GigaChat, но они недоступны")
    if backend == "huggingface":
        emb = _try_hf_embeddings()
        if emb:
            return emb, "huggingface"
        raise RuntimeError("Запрошены HuggingFace-эмбеддинги, но пакет не установлен")
    if backend == "tfidf":
        return TfidfEmbeddings(), "tfidf"

    for factory, name in (
        (_try_gigachat_embeddings, "gigachat"),
        (_try_hf_embeddings, "huggingface"),
    ):
        emb = factory()
        if emb:
            return emb, name
    logger.info("Эмбеддинги: локальный TF-IDF")
    return TfidfEmbeddings(), "tfidf"

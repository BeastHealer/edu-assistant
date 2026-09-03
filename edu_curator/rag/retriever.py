"""Поиск по базе знаний с фильтрами module / topic / resource_type."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from edu_curator.models import RetrievedChunk
from edu_curator.rag.embeddings import get_embeddings
from edu_curator.rag.indexer import LocalTfidfIndex

logger = logging.getLogger(__name__)


def _match_filter(metadata: dict[str, Any], filters: dict[str, str | None]) -> bool:
    for key, value in filters.items():
        if not value or value in {"Все", "all", "*"}:
            continue
        current = str(metadata.get(key, "")).lower()
        if current != str(value).lower():
            return False
    return True


def _to_chunk(text: str, metadata: dict[str, Any], score: float) -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        source=str(metadata.get("source", "")),
        doc_id=str(metadata.get("doc_id", "")),
        module=str(metadata.get("module", "")),
        topic=str(metadata.get("topic", "")),
        resource_type=str(metadata.get("resource_type", "")),
        difficulty=str(metadata.get("difficulty", "")),
        score=float(score),
        metadata=dict(metadata),
    )


class KnowledgeRetriever:
    def __init__(self) -> None:
        self.persist_dir = settings.chroma_dir
        self._tfidf: LocalTfidfIndex | None = None
        self._chroma = None
        self._backend = "unknown"
        self._load()

    def _load(self) -> None:
        tfidf_path = self.persist_dir / "tfidf.pkl"
        chroma_path = self.persist_dir / "chroma_store"
        if tfidf_path.exists() and not chroma_path.exists():
            self._tfidf = LocalTfidfIndex.load(self.persist_dir)
            self._backend = "tfidf"
            return
        if chroma_path.exists():
            try:
                from langchain_community.vectorstores import Chroma

                embeddings, name = get_embeddings()
                self._chroma = Chroma(
                    embedding_function=embeddings,
                    persist_directory=str(chroma_path),
                    collection_name=settings.chroma_collection,
                )
                self._backend = f"chroma:{name}"
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось открыть Chroma: %s", exc)
        if tfidf_path.exists():
            self._tfidf = LocalTfidfIndex.load(self.persist_dir)
            self._backend = "tfidf"
            return
        raise FileNotFoundError(
            "База знаний не проиндексирована. Запустите: python scripts/index_knowledge.py"
        )

    @property
    def backend(self) -> str:
        return self._backend

    def search(
        self,
        query: str,
        *,
        k: int | None = None,
        module: str | None = None,
        resource_type: str | None = None,
        topic: str | None = None,
    ) -> list[RetrievedChunk]:
        k = k or settings.retrieval_k
        filters = {"module": module, "resource_type": resource_type, "topic": topic}
        if self._tfidf is not None:
            return self._search_tfidf(query, k=k, filters=filters)
        return self._search_chroma(query, k=k, filters=filters)

    def _search_tfidf(self, query: str, k: int, filters: dict) -> list[RetrievedChunk]:
        index = self._tfidf
        assert index is not None and index.embeddings is not None and index.matrix is not None
        q = index.embeddings.vectorizer.transform([query])
        sims = cosine_similarity(q, index.matrix).ravel()
        order = np.argsort(-sims)
        results: list[RetrievedChunk] = []
        for idx in order:
            doc = index.documents[idx]
            if not _match_filter(doc.metadata, filters):
                continue
            results.append(_to_chunk(doc.page_content, doc.metadata, float(sims[idx])))
            if len(results) >= k:
                break
        return results

    def _search_chroma(self, query: str, k: int, filters: dict) -> list[RetrievedChunk]:
        assert self._chroma is not None
        where: dict[str, Any] = {}
        if filters.get("module") and filters["module"] not in {"Все", "all"}:
            where["module"] = filters["module"]
        if filters.get("resource_type") and filters["resource_type"] not in {"Все", "all"}:
            where["resource_type"] = filters["resource_type"]
        kwargs: dict[str, Any] = {"k": max(k * 3, k)}
        if where:
            kwargs["filter"] = where
        try:
            pairs = self._chroma.similarity_search_with_relevance_scores(query, **kwargs)
        except Exception:
            docs = self._chroma.similarity_search(query, **kwargs)
            pairs = [(d, 0.5) for d in docs]
        chunks: list[RetrievedChunk] = []
        for doc, score in pairs:
            if not _match_filter(doc.metadata, filters):
                continue
            chunks.append(_to_chunk(doc.page_content, doc.metadata, float(score)))
            if len(chunks) >= k:
                break
        return chunks

    def unique_values(self, field: str) -> list[str]:
        values: set[str] = set()
        if self._tfidf is not None:
            for doc in self._tfidf.documents:
                val = str(doc.metadata.get(field, "")).strip()
                if val:
                    values.add(val)
        elif self._chroma is not None:
            try:
                data = self._chroma.get(include=["metadatas"])
                for meta in data.get("metadatas") or []:
                    val = str((meta or {}).get(field, "")).strip()
                    if val:
                        values.add(val)
            except Exception:
                pass
        return sorted(values)

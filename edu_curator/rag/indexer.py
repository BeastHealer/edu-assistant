"""Индексация базы знаний в Chroma (с TF-IDF fallback без Chroma)."""

from __future__ import annotations

import json
import logging
import pickle
import shutil
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import settings
from edu_curator.rag.embeddings import TfidfEmbeddings, get_embeddings
from edu_curator.rag.loader import load_knowledge_documents, split_documents

logger = logging.getLogger(__name__)


class LocalTfidfIndex:
    """Простой локальный индекс, если Chroma недоступна или выбран TF-IDF."""

    def __init__(self, persist_dir: Path) -> None:
        self.persist_dir = persist_dir
        self.embeddings: TfidfEmbeddings | None = None
        self.documents: list[Document] = []
        self.matrix = None

    def build(self, chunks: list[Document], embeddings: TfidfEmbeddings) -> None:
        texts = [c.page_content for c in chunks]
        embeddings.fit(texts)
        self.embeddings = embeddings
        self.documents = chunks
        self.matrix = embeddings.vectorizer.transform(texts)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        with (self.persist_dir / "tfidf.pkl").open("wb") as fh:
            pickle.dump(
                {
                    "vectorizer": embeddings.vectorizer,
                    "texts": texts,
                    "metadatas": [c.metadata for c in chunks],
                },
                fh,
            )

    @classmethod
    def load(cls, persist_dir: Path) -> "LocalTfidfIndex":
        path = persist_dir / "tfidf.pkl"
        if not path.exists():
            raise FileNotFoundError(f"Нет индекса {path}. Запустите scripts/index_knowledge.py")
        with path.open("rb") as fh:
            payload = pickle.load(fh)
        index = cls(persist_dir)
        emb = TfidfEmbeddings()
        emb.vectorizer = payload["vectorizer"]
        emb._fitted = True
        index.embeddings = emb
        index.documents = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(payload["texts"], payload["metadatas"], strict=True)
        ]
        index.matrix = emb.vectorizer.transform(payload["texts"])
        return index


def _try_chroma(chunks: list[Document], embeddings: Embeddings, persist_dir: Path, collection: str):
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError:
        from langchain_chroma import Chroma  # type: ignore[import-not-found]

    persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist_dir / "chroma_store"),
        collection_name=collection,
    )


def index_knowledge(*, force: bool = False) -> dict:
    persist_dir = settings.chroma_dir
    if force and persist_dir.exists():
        shutil.rmtree(persist_dir)
        get_embeddings.cache_clear()
    persist_dir.mkdir(parents=True, exist_ok=True)
    marker = persist_dir / "index_meta.json"

    documents = load_knowledge_documents()
    chunks = split_documents(documents)
    embeddings, backend = get_embeddings()

    if isinstance(embeddings, TfidfEmbeddings) or backend == "tfidf":
        if not isinstance(embeddings, TfidfEmbeddings):
            embeddings = TfidfEmbeddings()
            backend = "tfidf"
        index = LocalTfidfIndex(persist_dir)
        index.build(chunks, embeddings)
        store_kind = "tfidf"
    else:
        try:
            _try_chroma(chunks, embeddings, persist_dir, settings.chroma_collection)
            store_kind = "chroma"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chroma недоступна (%s), переключаюсь на TF-IDF", exc)
            tfidf = TfidfEmbeddings()
            LocalTfidfIndex(persist_dir).build(chunks, tfidf)
            store_kind = "tfidf"
            backend = "tfidf"

    meta = {
        "documents": len(documents),
        "chunks": len(chunks),
        "embedding_backend": backend,
        "store": store_kind,
        "collection": settings.chroma_collection,
    }
    marker.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Индекс готов: %s", meta)
    return meta

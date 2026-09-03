"""Чтение markdown-базы знаний и нарезка чанков с метаданными."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings

logger = logging.getLogger(__name__)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def parse_markdown(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("'\"")
    return meta, match.group(2).strip()


def load_knowledge_documents(knowledge_dir: Path | None = None) -> list[Document]:
    root = knowledge_dir or settings.knowledge_dir
    docs: list[Document] = []
    for path in sorted(root.rglob("*.md")):
        meta, body = parse_markdown(path)
        metadata = {
            "source": str(path.relative_to(root)).replace("\\", "/"),
            "doc_id": str(meta.get("doc_id", path.stem)),
            "module": str(meta.get("module", "")),
            "module_title": str(meta.get("module_title", "")),
            "topic": str(meta.get("topic", "")),
            "resource_type": str(meta.get("resource_type", "")),
            "difficulty": str(meta.get("difficulty", "")),
            "week": str(meta.get("week", "")),
            "title": body.split("\n", 1)[0].lstrip("# ").strip() if body else path.stem,
        }
        docs.append(Document(page_content=body, metadata=metadata))
    logger.info("Загружено документов базы знаний: %s", len(docs))
    return docs


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{chunk.metadata.get('doc_id', 'doc')}-{i}"
    return chunks

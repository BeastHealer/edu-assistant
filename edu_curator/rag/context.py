"""Сборка контекста RAG для промпта."""

from __future__ import annotations

from edu_curator.models import RetrievedChunk


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "В базе знаний не найдено релевантных фрагментов."
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[{i}] doc_id={chunk.doc_id} | module={chunk.module} | "
            f"type={chunk.resource_type} | topic={chunk.topic} | source={chunk.source}\n"
            f"{chunk.text.strip()}"
        )
    return "\n\n".join(blocks)


def format_sources_footer(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "Источники: в базе знаний нет достаточно близких фрагментов — ответ может быть неполным."
    seen: set[str] = set()
    lines = ["Источники:"]
    for chunk in chunks:
        key = chunk.doc_id or chunk.source
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- [{chunk.doc_id} · {chunk.module} · {chunk.resource_type}] {chunk.topic} ({chunk.source})")
    return "\n".join(lines)

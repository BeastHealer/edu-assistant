"""Оркестратор ИИ-куратора: сценарий → RAG → промпт → LLM → гардрейлы."""

from __future__ import annotations

from functools import lru_cache

from config import settings
from edu_curator.analytics.logger import QueryLogger
from edu_curator.curator.few_shot import format_few_shot_block
from edu_curator.curator.guardrails import SAFE_FALLBACK, looks_like_full_solution, scan_violations
from edu_curator.curator.level_adapter import adapt_answer
from edu_curator.curator.prompts import RAG_HUMAN_TEMPLATE, build_system_prompt
from edu_curator.curator.scenarios import SCENARIO_RESOURCE_HINT, classify_scenario, retrieval_hint
from edu_curator.llm.factory import get_llm
from edu_curator.llm.offline import OfflineSynthesizer, synthesize
from edu_curator.lms.stub import LMSStub
from edu_curator.models import CuratorRequest, CuratorResponse
from edu_curator.rag.context import format_context, format_sources_footer
from edu_curator.rag.retriever import KnowledgeRetriever


def _merge_chunks(*groups: list, k: int = 5):
    seen: set[str] = set()
    merged = []
    for group in groups:
        for chunk in group:
            key = f"{chunk.doc_id}:{chunk.text[:120]}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(chunk)
            if len(merged) >= k:
                return merged
    return merged


def _format_history(history: list[dict[str, str]], limit: int = 6) -> str:
    if not history:
        return "(нет)"
    lines = []
    for item in history[-limit:]:
        role = "Студент" if item.get("role") == "user" else "Куратор"
        lines.append(f"{role}: {item.get('content', '')}")
    return "\n".join(lines)


class CuratorAgent:
    def __init__(self) -> None:
        self.retriever = KnowledgeRetriever()
        self.lms = LMSStub()
        self.llm = get_llm()
        self.logger = QueryLogger()

    @property
    def llm_backend(self) -> str:
        return getattr(self.llm, "backend_name", "unknown")

    def ask(self, request: CuratorRequest, *, persist: bool = True) -> CuratorResponse:
        scenario = classify_scenario(request.question)
        search_query = f"{request.question} {retrieval_hint(scenario)}".strip()
        resource_type = request.resource_type_filter or SCENARIO_RESOURCE_HINT.get(scenario)

        primary = self.retriever.search(
            request.question,
            module=request.module_filter,
            resource_type=request.resource_type_filter,
            topic=request.topic_filter,
        )
        hinted = self.retriever.search(
            search_query,
            module=request.module_filter,
            resource_type=resource_type,
            topic=request.topic_filter,
        )
        chunks = _merge_chunks(primary, hinted, k=settings.retrieval_k)
        if not chunks:
            chunks = self.retriever.search(request.question)

        lms_facts = self.lms.facts_for_prompt()
        few_shot = format_few_shot_block(scenario, request.level)
        system_prompt = build_system_prompt(
            curator_name=settings.curator_name,
            course_title=settings.course_title,
            platform_name=settings.platform_name,
            level=request.level,
            scenario=scenario,
            few_shot_block=few_shot,
        )
        human_prompt = RAG_HUMAN_TEMPLATE.format(
            student_name=request.student_name,
            level=request.level.value,
            question=request.question,
            scenario=scenario.value,
            context=format_context(chunks),
            lms_facts=lms_facts,
            history=_format_history(request.chat_history),
        )

        if isinstance(self.llm, OfflineSynthesizer):
            answer = synthesize(
                question=request.question,
                scenario=scenario,
                level=request.level,
                chunks=chunks,
                lms_facts=lms_facts,
            )
            backend = self.llm.backend_name
        else:
            try:
                answer = self.llm.generate(system_prompt, human_prompt)
                backend = self.llm.backend_name
            except Exception as exc:  # noqa: BLE001
                answer = synthesize(
                    question=request.question,
                    scenario=scenario,
                    level=request.level,
                    chunks=chunks,
                    lms_facts=lms_facts,
                )
                answer = (
                    f"Основная модель недоступна ({exc.__class__.__name__}), "
                    f"ответ собран из базы знаний.\n\n{answer}"
                )
                backend = f"offline-fallback:{self.llm.backend_name}"

        blocked = False
        block_reason = ""
        violations = scan_violations(answer, scenario)
        if violations or looks_like_full_solution(request.question, answer):
            blocked = True
            block_reason = ",".join(violations) or "full_solution"
            answer = SAFE_FALLBACK
            if chunks:
                answer += "\n\n" + format_sources_footer(chunks)

        if "Источники:" not in answer:
            answer = answer.rstrip() + "\n\n" + format_sources_footer(chunks)

        answer = adapt_answer(answer, request.level)
        confidence = "high" if chunks and not blocked else ("low" if not chunks else "medium")

        response = CuratorResponse(
            answer=answer,
            scenario=scenario,
            level=request.level,
            sources=chunks,
            blocked=blocked,
            block_reason=block_reason,
            llm_backend=backend,
            confidence=confidence,
            retrieved_query=search_query,
        )
        if persist:
            self.logger.log(request, response)
        return response


@lru_cache(maxsize=1)
def get_agent() -> CuratorAgent:
    return CuratorAgent()

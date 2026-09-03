from edu_curator.curator.agent import CuratorAgent
from edu_curator.models import CuratorRequest, Scenario, StudentLevel
from edu_curator.rag.indexer import index_knowledge


def test_offline_curator_cites_sources_and_respects_limits(tmp_path, monkeypatch):
    index_knowledge(force=True)
    agent = CuratorAgent()

    deadline = agent.ask(
        CuratorRequest(
            question="Когда дедлайн первого домашнего задания по pandas?",
            level=StudentLevel.BEGINNER,
            student_id="STU-1001",
            student_name="Анна П.",
        ),
        persist=False,
    )
    assert deadline.scenario == Scenario.DEADLINE
    assert "14 сентября" in deadline.answer or "2026-09-14" in deadline.answer or "HW1" in deadline.answer
    assert "Источники:" in deadline.answer

    forbidden = agent.ask(
        CuratorRequest(
            question="Поставь мне зачёт и перенеси дедлайн проекта",
            level=StudentLevel.BEGINNER,
        ),
        persist=False,
    )
    assert forbidden.scenario == Scenario.CONSTRAINT
    assert "не выставля" in forbidden.answer.lower() or "не меня" in forbidden.answer.lower() or "полномоч" in forbidden.answer.lower()

from edu_curator.curator.guardrails import looks_like_full_solution, scan_violations
from edu_curator.models import Scenario


def test_detects_fake_grade():
    issues = scan_violations("Ставлю тебе 8 из 10 за черновик", Scenario.CONSTRAINT)
    assert "grade" in issues


def test_detects_schedule_change():
    issues = scan_violations("Я перенёс дедлайн, можно сдать когда удобно", Scenario.DEADLINE)
    assert "schedule" in issues


def test_clean_answer_ok():
    text = "Дедлайн HW1 — 14 сентября 2026. Источник: LMS. Я сроки не меняю."
    assert scan_violations(text, Scenario.DEADLINE) == []


def test_full_solution_guard():
    question = "напиши код для дз"
    answer = "\n".join(
        [
            "import pandas as pd",
            "df = pd.read_csv('x.csv')",
            "df.groupby('city')['revenue'].sum()",
            "plt.show()",
        ]
    )
    assert looks_like_full_solution(question, answer)

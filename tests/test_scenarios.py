from edu_curator.curator.scenarios import classify_scenario
from edu_curator.models import Scenario


def test_deadline_question():
    assert classify_scenario("Когда дедлайн первого ДЗ?") == Scenario.DEADLINE


def test_constraint_grade():
    assert classify_scenario("Поставь мне зачёт по домашке") == Scenario.CONSTRAINT


def test_constraint_shift_deadline():
    assert classify_scenario("Перенеси дедлайн проекта на неделю") == Scenario.CONSTRAINT


def test_difficulty():
    assert classify_scenario("Я ничего не понимаю в корреляции, слишком сложно") == Scenario.DIFFICULTY


def test_recommendation():
    assert classify_scenario("Что почитать дополнительно по pandas?") == Scenario.RECOMMENDATION


def test_assignment_not_full_solution_request_is_help():
    assert classify_scenario("Какие критерии у итогового проекта?") == Scenario.ASSIGNMENT_HELP

from pathlib import Path

from src.automaton.model import Automaton
from src.automaton.parser import parse
from src.automaton.validator import is_deterministic, validate

FIXTURES = Path(__file__).parent / "fixtures"


def _pdf_automaton() -> Automaton:
    return parse((FIXTURES / "pdf_example.txt").read_text())


def test_pdf_example_is_valid():
    is_valid, violations = validate(_pdf_automaton())
    assert is_valid
    assert violations == []


def test_non_positive_n_is_invalid():
    automaton = Automaton(n=0, m=2, starts=set(), finals=set(), transitions={})
    is_valid, violations = validate(automaton)
    assert not is_valid
    assert any("n должно быть положительным" in v for v in violations)


def test_start_state_out_of_range():
    automaton = _pdf_automaton()
    automaton.starts = {5}
    is_valid, violations = validate(automaton)
    assert not is_valid
    assert any("стартовое состояние" in v for v in violations)


def test_transition_from_nonexistent_state():
    automaton = _pdf_automaton()
    automaton.transitions[(10, 0)] = {1}
    is_valid, violations = validate(automaton)
    assert not is_valid
    assert any("несуществующего состояния" in v for v in violations)


def test_transition_with_invalid_symbol():
    automaton = _pdf_automaton()
    automaton.transitions[(0, 9)] = {1}
    is_valid, violations = validate(automaton)
    assert not is_valid
    assert any("несуществующему символу" in v for v in violations)


def test_transition_to_nonexistent_state():
    automaton = _pdf_automaton()
    automaton.transitions[(0, 0)].add(99)
    is_valid, violations = validate(automaton)
    assert not is_valid
    assert any("в несуществующее состояние" in v for v in violations)


def test_pdf_example_is_not_deterministic():
    # transitions[(0,0)] = {1,2} — два состояния для одного (state,symbol), это NFA
    assert not is_deterministic(_pdf_automaton())


def test_single_start_and_single_target_transitions_is_deterministic():
    automaton = Automaton(n=2, m=1, starts={0}, finals={1}, transitions={(0, 0): {1}})
    assert is_deterministic(automaton)


def test_multiple_start_states_is_not_deterministic():
    automaton = Automaton(n=2, m=1, starts={0, 1}, finals={1}, transitions={(0, 0): {1}})
    assert not is_deterministic(automaton)


def test_partial_dfa_without_transition_for_every_symbol_is_still_deterministic():
    automaton = Automaton(n=2, m=2, starts={0}, finals={1}, transitions={(0, 0): {1}})
    assert is_deterministic(automaton)


def test_alphabet_size_matches_testcase():
    is_valid, violations = validate(_pdf_automaton(), expected_alphabet_size=2)
    assert is_valid
    assert violations == []


def test_alphabet_size_mismatch_is_invalid():
    # Как chatgpt/employer/run_018: заявлено m=2, а в алфавите задачи 12 символов. Все переходы
    # при этом в диапазоне [0, m) — без сверки с задачей такое прошло бы как корректное.
    is_valid, violations = validate(_pdf_automaton(), expected_alphabet_size=12)
    assert not is_valid
    assert any("не совпадает с алфавитом задачи" in v for v in violations)


def test_overstated_n_is_invalid():
    # Как chatgpt/basic/run_012: заявлено больше состояний, чем реально есть в автомате.
    automaton = _pdf_automaton()
    automaton.n = 5  # используются только 0, 1, 2
    is_valid, violations = validate(automaton)
    assert not is_valid
    assert any("заявлено n=5, но 2 состояний нигде не упоминаются" in v and "3, 4" in v for v in violations)


def test_state_mentioned_only_as_final_counts_as_used():
    # Изолированное состояние, которое только финальное (без переходов), — не "фантом":
    # оно упомянуто, просто недостижимо. Недостижимость — не ошибка формата.
    automaton = Automaton(n=2, m=1, starts={0}, finals={1}, transitions={(0, 0): {0}})
    is_valid, violations = validate(automaton)
    assert is_valid
    assert violations == []

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

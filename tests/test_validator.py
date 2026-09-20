from pathlib import Path

from src.automaton.model import Automaton
from src.automaton.parser import parse
from src.automaton.validator import validate

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
